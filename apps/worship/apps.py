from django.apps import AppConfig


class WorshipConfig(AppConfig):
    """Configuration de l'application Worship."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.worship'
    verbose_name = 'Liturgie & Cultes'

    def ready(self):
        """Import des signaux au démarrage."""
        import apps.worship.signals  # noqa
