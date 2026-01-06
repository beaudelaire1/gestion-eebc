from django.apps import AppConfig


class MembersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.members'
    verbose_name = 'Membres'
    
    def ready(self):
        """Importer les signals lors du démarrage de l'app."""
        import apps.members.signals