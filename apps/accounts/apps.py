from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Comptes Utilisateurs'

    def ready(self):
        from . import signals  # noqa: F401

        # Replace legacy account-wide lockouts with shared IP+account throttling.
        from .services import AuthenticationService
        from .security_auth import secure_authenticate_user
        AuthenticationService.authenticate_user = classmethod(secure_authenticate_user)
