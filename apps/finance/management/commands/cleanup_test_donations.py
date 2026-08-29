"""
Management command pour nettoyer les dons Stripe de test.

Supprime les ``OnlineDonation`` dont le ``stripe_session_id`` commence
par ``cs_test_`` (mode test Stripe) ainsi que la ``FinancialTransaction``
associée, afin de ne pas polluer la trésorerie avec des paiements de test.

Exemples d'utilisation :

    # Prévisualisation (aucune suppression)
    python manage.py cleanup_test_donations --dry-run

    # Supprimer tous les dons de test
    python manage.py cleanup_test_donations

    # Supprimer uniquement un don précis
    python manage.py cleanup_test_donations --session-id cs_test_a1b2c3

    # Supprimer uniquement le dernier don de test
    python manage.py cleanup_test_donations --last
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction

from apps.finance.models import OnlineDonation


class Command(BaseCommand):
    help = "Supprime les dons Stripe de test (cs_test_*) et leur transaction associée."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Affiche ce qui serait supprimé, sans rien modifier.",
        )
        parser.add_argument(
            '--session-id',
            type=str,
            default=None,
            help="Supprime uniquement le don ayant ce stripe_session_id.",
        )
        parser.add_argument(
            '--last',
            action='store_true',
            help="Supprime uniquement le dernier don de test créé.",
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help="Ne demande pas de confirmation.",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        session_id = options['session_id']
        only_last = options['last']
        auto_confirm = options['yes']

        queryset = OnlineDonation.objects.select_related('transaction')

        if session_id:
            queryset = queryset.filter(stripe_session_id=session_id)
        else:
            queryset = queryset.filter(stripe_session_id__startswith='cs_test_')

        if only_last:
            queryset = queryset.order_by('-created_at')[:1]
        else:
            queryset = queryset.order_by('-created_at')

        donations = list(queryset)

        if not donations:
            self.stdout.write(self.style.WARNING("Aucun don de test trouvé."))
            return

        self.stdout.write(self.style.NOTICE(f"\n{len(donations)} don(s) à supprimer :\n"))
        for donation in donations:
            tx = donation.transaction
            tx_info = (
                f"transaction #{tx.id} ({tx.reference})"
                if tx
                else "sans transaction"
            )
            self.stdout.write(
                f"  - Don #{donation.id} | {donation.amount}€ | "
                f"{donation.donor_email or '(sans email)'} | "
                f"{donation.stripe_session_id} | {tx_info}"
            )

        if dry_run:
            self.stdout.write(self.style.SUCCESS("\n[DRY RUN] Aucune suppression effectuée."))
            return

        if not auto_confirm:
            answer = input("\nConfirmer la suppression ? [y/N] ").strip().lower()
            if answer not in ('y', 'yes', 'o', 'oui'):
                raise CommandError("Annulé par l'utilisateur.")

        deleted_donations = 0
        deleted_transactions = 0

        with db_transaction.atomic():
            for donation in donations:
                tx = donation.transaction
                donation.delete()
                deleted_donations += 1
                if tx:
                    # FinancialTransaction utilise soft-delete,
                    # on force la suppression réelle pour les données de test
                    if hasattr(tx, 'hard_delete'):
                        tx.hard_delete()
                    else:
                        type(tx).all_objects.filter(pk=tx.pk).delete()
                    deleted_transactions += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nOK — {deleted_donations} don(s) et "
            f"{deleted_transactions} transaction(s) supprimés."
        ))
