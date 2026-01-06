"""
Commande de gestion pour nettoyer les anciens logs d'emails.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.communication.models import EmailLog


class Command(BaseCommand):
    help = 'Nettoie les anciens logs d\'emails selon la politique de rétention'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Nombre de jours à conserver (défaut: 365)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Afficher ce qui serait supprimé sans effectuer la suppression'
        )
        parser.add_argument(
            '--keep-failed',
            action='store_true',
            help='Conserver les emails échoués même s\'ils sont anciens'
        )

    def handle(self, *args, **options):
        """Nettoie les anciens logs d'emails."""
        
        days = options['days']
        dry_run = options['dry_run']
        keep_failed = options['keep_failed']
        
        # Calculer la date limite
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Construire la requête
        queryset = EmailLog.objects.filter(created_at__lt=cutoff_date)
        
        if keep_failed:
            # Exclure les emails échoués
            queryset = queryset.exclude(status=EmailLog.Status.FAILED)
        
        # Compter les logs à supprimer
        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ Aucun log à supprimer.')
            )
            return
        
        # Afficher les statistiques
        stats = {
            'sent': queryset.filter(status=EmailLog.Status.SENT).count(),
            'failed': queryset.filter(status=EmailLog.Status.FAILED).count(),
            'pending': queryset.filter(status=EmailLog.Status.PENDING).count(),
        }
        
        self.stdout.write(f'\n📊 Logs à supprimer (plus de {days} jours):')
        self.stdout.write(f'  • Total: {total_count}')
        self.stdout.write(f'  • Envoyés: {stats["sent"]}')
        self.stdout.write(f'  • Échoués: {stats["failed"]}')
        self.stdout.write(f'  • En attente: {stats["pending"]}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n🔍 Mode dry-run: aucune suppression effectuée.')
            )
            return
        
        # Demander confirmation
        confirm = input('\n❓ Confirmer la suppression ? (oui/non): ')
        if confirm.lower() not in ['oui', 'o', 'yes', 'y']:
            self.stdout.write(
                self.style.WARNING('❌ Suppression annulée.')
            )
            return
        
        # Effectuer la suppression
        deleted_count, _ = queryset.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ {deleted_count} logs supprimés avec succès.')
        )
        
        # Afficher les statistiques finales
        remaining_count = EmailLog.objects.count()
        self.stdout.write(f'📈 Logs restants: {remaining_count}')
        
        # Afficher les statistiques des derniers 30 jours
        recent_stats = EmailLog.get_stats(days=30)
        self.stdout.write(f'\n📊 Statistiques des 30 derniers jours:')
        self.stdout.write(f'  • Total: {recent_stats["total"]}')
        self.stdout.write(f'  • Taux de succès: {recent_stats["success_rate"]}%')
        self.stdout.write(f'  • Taux d\'échec: {recent_stats["failure_rate"]}%')