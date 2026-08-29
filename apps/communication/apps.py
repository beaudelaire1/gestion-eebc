from django.apps import AppConfig


class CommunicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.communication'
    verbose_name = 'Communication'
    
    def ready(self):
        # Importer les signaux et les tâches de canal pour les enregistrer.
        import apps.communication.channel_tasks  # noqa: F401
        import apps.communication.signals  # noqa: F401
