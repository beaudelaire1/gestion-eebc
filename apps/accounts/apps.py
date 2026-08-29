from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Comptes Utilisateurs'

    def ready(self):
        # Register token-revocation hooks for privilege/password/MFA changes.
        from . import signals  # noqa: F401
