from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core - Sites & Familles'
    
    def ready(self):
        """Connecte les signals au démarrage de l'application."""
        # Import des signals pour les connecter
        import apps.core.signals  # noqa: F401
