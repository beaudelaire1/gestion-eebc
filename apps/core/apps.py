import os

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.safestring import mark_safe


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core - Sites & Familles'

    def ready(self):
        """Connecte les signaux et applique les invariants de sécurité globaux."""
        import apps.core.signals  # noqa: F401

        # FILE_UPLOAD_MAX_MEMORY_SIZE is an in-memory threshold, not a maximum
        # upload size. Large media must spool to disk/storage instead of allowing
        # hundreds of MiB per request to live in a worker process.
        settings.FILE_UPLOAD_MAX_MEMORY_SIZE = min(
            int(getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 5 * 1024 * 1024)),
            5 * 1024 * 1024,
        )
        settings.DATA_UPLOAD_MAX_MEMORY_SIZE = min(
            int(getattr(settings, 'DATA_UPLOAD_MAX_MEMORY_SIZE', 10 * 1024 * 1024)),
            10 * 1024 * 1024,
        )

        settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')
        is_production = settings_module.endswith('.prod')

        # Security counters must be shared between Gunicorn workers in prod.
        if is_production:
            backend = settings.CACHES.get('default', {}).get('BACKEND', '')
            if 'locmem' in backend.lower():
                raise ImproperlyConfigured(
                    'Production security requires a shared cache. Configure REDIS_URL; '
                    'LocMemCache cannot provide reliable rate limiting across workers.'
                )

        # Forwarded client addresses are trusted only from explicitly configured
        # reverse proxies. CIDR notation is supported, e.g. 10.0.0.0/8.
        proxy_env = os.environ.get('TRUSTED_PROXY_IPS', '').strip()
        if proxy_env:
            settings.TRUSTED_PROXY_IPS = [
                value.strip() for value in proxy_env.split(',') if value.strip()
            ]
        elif is_production:
            raise ImproperlyConfigured(
                'Configure TRUSTED_PROXY_IPS with the IP/CIDR of the reverse proxy. '
                'X-Forwarded-For is intentionally ignored without this trust boundary.'
            )
        else:
            settings.TRUSTED_PROXY_IPS = ['127.0.0.1/32', '::1/128']

        from apps.core.security import get_trusted_client_ip
        from apps.core.middleware import RateLimitMiddleware, SessionTimeoutMiddleware
        RateLimitMiddleware._get_client_ip = staticmethod(get_trusted_client_ip)
        SessionTimeoutMiddleware._get_client_ip = staticmethod(get_trusted_client_ip)

        try:
            from apps.accounts.services import AuthenticationService
            AuthenticationService.get_client_ip = staticmethod(get_trusted_client_ip)
        except Exception:
            pass

        try:
            from apps.api import views as api_views
            api_views._get_client_ip = get_trusted_client_ip
        except Exception:
            pass

        # Hotfix Jazzmin pagination: certaines versions appellent format_html sans args.
        try:
            from jazzmin.templatetags import jazzmin as jazzmin_tags

            original_format_html = jazzmin_tags.format_html

            def _safe_jazzmin_format_html(format_string, *args, **kwargs):
                if not args and not kwargs:
                    return mark_safe(format_string)
                return original_format_html(format_string, *args, **kwargs)

            jazzmin_tags.format_html = _safe_jazzmin_format_html
        except Exception:
            pass
