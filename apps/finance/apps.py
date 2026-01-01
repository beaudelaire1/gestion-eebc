from django.apps import AppConfig


class FinanceConfig(AppConfig):
    """Configuration de l'application Finance."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.finance'
    verbose_name = 'Finance & Trésorerie'

    def ready(self):
        """Import des signaux au démarrage."""
        import apps.finance.signals  # noqa
