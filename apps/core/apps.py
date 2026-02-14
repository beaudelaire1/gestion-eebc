from django.apps import AppConfig
from django.utils.safestring import mark_safe


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core - Sites & Familles'
    
    def ready(self):
        """Connecte les signals au démarrage de l'application."""
        # Import des signals pour les connecter
        import apps.core.signals  # noqa: F401

        # Hotfix Jazzmin pagination: certaines versions appellent format_html sans args
        # ce qui déclenche TypeError sur certaines versions de Django.
        try:
            from jazzmin.templatetags import jazzmin as jazzmin_tags

            original_format_html = jazzmin_tags.format_html

            def _safe_jazzmin_format_html(format_string, *args, **kwargs):
                if not args and not kwargs:
                    return mark_safe(format_string)
                return original_format_html(format_string, *args, **kwargs)

            jazzmin_tags.format_html = _safe_jazzmin_format_html
        except Exception:
            # Ne pas bloquer le démarrage si Jazzmin est indisponible
            pass
