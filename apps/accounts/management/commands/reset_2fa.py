"""Remettre à zéro la 2FA d'un compte pour qu'il puisse s'enrôler à nouveau.

La page de configuration invite l'utilisateur bloqué à contacter le support.
Sans cette commande, le support n'a aucun moyen d'agir : les champs 2FA ne sont
pas exposés dans l'admin Django, et ``enable_2fa`` ne sait qu'activer un compte
déjà configuré.

Cas visé : téléphone perdu, changé ou réinitialisé, application désinstallée.
Le compte repart de zéro et reflashe un QR code à la prochaine connexion.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.accounts.two_factor_policy import requires_2fa_enrollment


class Command(BaseCommand):
    help = (
        "Efface le secret TOTP et les codes de secours d'un utilisateur afin "
        "qu'il reconfigure sa 2FA depuis un nouveau téléphone."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "username",
            help="Nom d'utilisateur du compte à réinitialiser.",
        )
        parser.add_argument(
            "--status",
            action="store_true",
            help="Affiche uniquement l'état 2FA sans rien modifier.",
        )

    def handle(self, *args, **options):
        username = options["username"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"Utilisateur introuvable : {username}") from exc

        has_secret = bool((user.two_factor_secret or "").strip())

        if options["status"]:
            self.stdout.write(
                " | ".join(
                    [
                        f"username={user.username}",
                        f"enabled={user.two_factor_enabled}",
                        f"confirmed={user.two_factor_confirmed}",
                        f"secret={'present' if has_secret else 'missing'}",
                    ]
                )
            )
            return

        if not user.two_factor_enabled and not has_secret:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Rien à réinitialiser : {user.username} n'a aucune 2FA configurée."
                )
            )
            return

        user.disable_two_factor()

        self.stdout.write(
            self.style.SUCCESS(
                f"2FA réinitialisée pour {user.username}. "
                "Secret et codes de secours effacés."
            )
        )

        # Rafraîchir depuis la base : disable_two_factor a modifié l'instance,
        # et la politique se lit sur l'état réellement enregistré.
        user.refresh_from_db()
        if requires_2fa_enrollment(user):
            self.stdout.write(
                "Ce compte porte un rôle privilégié : il sera redirigé vers la "
                "page de configuration à sa prochaine connexion, et devra "
                "flasher un nouveau QR code pour retrouver l'accès."
            )
        else:
            self.stdout.write(
                "Ce compte peut se reconnecter avec son seul mot de passe. "
                "La 2FA reste facultative pour son rôle."
            )
