from django.apps import AppConfig


class BibleclubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bibleclub'
    verbose_name = 'Club Biblique'

    def ready(self):
        import apps.bibleclub.signals  # noqa: F401

