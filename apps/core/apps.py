import os

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


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

        # Client IP trust boundary.
        # - Traditional reverse proxies: trust X-Forwarded-For only when the socket
        #   peer belongs to an explicitly configured CIDR.
        # - Render: trust only Cloudflare's overwrite-safe CF-Connecting-IP header.
        proxy_env = os.environ.get('TRUSTED_PROXY_IPS', '').strip()
        trusted_header = str(
            getattr(settings, 'TRUSTED_CLIENT_IP_HEADER', '') or ''
        ).strip()

        if trusted_header and trusted_header != 'HTTP_CF_CONNECTING_IP':
            raise ImproperlyConfigured(
                'Unsupported TRUSTED_CLIENT_IP_HEADER. '
                'Only HTTP_CF_CONNECTING_IP is accepted as a dedicated trusted header.'
            )

        if proxy_env:
            settings.TRUSTED_PROXY_IPS = [
                value.strip() for value in proxy_env.split(',') if value.strip()
            ]
        elif is_production and not trusted_header:
            raise ImproperlyConfigured(
                'Configure TRUSTED_CLIENT_IP_HEADER=HTTP_CF_CONNECTING_IP on Render '
                'or TRUSTED_PROXY_IPS with explicit reverse-proxy CIDRs. '
                'X-Forwarded-For is intentionally ignored without a trust boundary.'
            )
        elif is_production:
            settings.TRUSTED_PROXY_IPS = []
        else:
            settings.TRUSTED_PROXY_IPS = ['127.0.0.1/32', '::1/128']

        from apps.core.security import get_trusted_client_ip
        from apps.core.middleware import RateLimitMiddleware, SessionTimeoutMiddleware

        RateLimitMiddleware._get_client_ip = staticmethod(get_trusted_client_ip)
        SessionTimeoutMiddleware._get_client_ip = staticmethod(get_trusted_client_ip)

        try:
            from apps.accounts.services import AuthenticationService

            AuthenticationService.get_client_ip = staticmethod(get_trusted_client_ip)
        except ImportError:
            pass

        try:
            from apps.api import views as api_views

            api_views._get_client_ip = get_trusted_client_ip
        except ImportError:
            pass
