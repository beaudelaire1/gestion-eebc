from django.apps import AppConfig


class CampaignsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.campaigns'
    verbose_name = 'Campagnes'

    def ready(self):
        import apps.campaigns.signals  # noqa: F401

