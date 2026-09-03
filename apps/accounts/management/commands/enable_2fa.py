"""Repair/enable 2FA state for an already configured account."""

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = (
        "Active la 2FA en base pour un utilisateur qui possède déjà un secret TOTP. "
        "La commande refuse d'activer un compte qui n'a jamais été configuré."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "username",
            help="Nom d'utilisateur du compte à vérifier/activer.",
        )
        parser.add_argument(
            "--status",
            action="store_true",
            help="Affiche uniquement l'état 2FA sans modifier la base.",
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

        if not has_secret:
            raise CommandError(
                "Activation refusée : ce compte ne possède aucun secret TOTP. "
                "Configurez d'abord la 2FA depuis le profil afin de scanner le QR code."
            )

        fields_to_update = []
        if not user.two_factor_enabled:
            user.two_factor_enabled = True
            fields_to_update.append("two_factor_enabled")

        if not user.two_factor_confirmed:
            user.two_factor_confirmed = True
            fields_to_update.append("two_factor_confirmed")

        if fields_to_update:
            user.save(update_fields=fields_to_update)
            self.stdout.write(
                self.style.SUCCESS(
                    f"2FA activée en base pour {user.username} "
                    f"({', '.join(fields_to_update)})."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"2FA déjà active et confirmée pour {user.username}."
                )
            )
