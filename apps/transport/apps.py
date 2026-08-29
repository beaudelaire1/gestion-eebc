from django.apps import AppConfig


class TransportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.transport'
    verbose_name = 'Transport'
    
    def ready(self):
        """Enregistrer les signaux lors du démarrage de l'app."""
        import apps.transport.signals  # noqa

