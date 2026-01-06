"""
Commande de gestion pour afficher les statistiques d'emails.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.communication.models import EmailLog


class Command(BaseCommand):
    help = 'Affiche les statistiques d\'envoi d\'emails'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Nombre de jours à analyser (défaut: 30)'
        )
        parser.add_argument(
            '--show-errors',
            action='store_true',
            help='Afficher le détail des erreurs'
        )

    def handle(self, *args, **options):
        """Affiche les statistiques d'emails."""
        
        days = options['days']
        show_errors = options['show_errors']
        
        self.stdout.write(f'\n📊 Statistiques d\'emails - {days} derniers jours\n')
        
        # Statistiques générales
        stats = EmailLog.get_stats(days=days)
        
        self.stdout.write('📈 Vue d\'ensemble:')
        self.stdout.write(f'  • Total d\'emails: {stats["total"]}')
        self.stdout.write(f'  • Envoyés avec succès: {stats["sent"]} ({stats["success_rate"]}%)')
        self.stdout.write(f'  • Échecs: {stats["failed"]} ({stats["failure_rate"]}%)')
        self.stdout.write(f'  • En attente: {stats["pending"]}')
        
        if stats["total"] == 0:
            self.stdout.write(
                self.style.WARNING('\n⚠️  Aucun email trouvé pour cette période.')
            )
            return
        
        # Statistiques par type de template
        since = timezone.now() - timedelta(days=days)
        
        template_stats = EmailLog.objects.filter(
            created_at__gte=since
        ).values('template_type').distinct()
        
        if template_stats:
            self.stdout.write('\n📋 Par type de template:')
            for template_stat in template_stats:
                template_type = template_stat['template_type'] or 'Non spécifié'
                
                template_logs = EmailLog.objects.filter(
                    created_at__gte=since,
                    template_type=template_stat['template_type']
                )
                
                total = template_logs.count()
                sent = template_logs.filter(status=EmailLog.Status.SENT).count()
                failed = template_logs.filter(status=EmailLog.Status.FAILED).count()
                
                success_rate = round((sent / total * 100) if total > 0 else 0, 1)
                
                self.stdout.write(f'  • {template_type}: {total} emails ({success_rate}% succès)')
        
        # Top 10 des destinataires
        top_recipients = EmailLog.objects.filter(
            created_at__gte=since
        ).values('recipient_email').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10]
        
        if top_recipients:
            self.stdout.write('\n👥 Top 10 des destinataires:')
            for i, recipient in enumerate(top_recipients, 1):
                self.stdout.write(f'  {i:2d}. {recipient["recipient_email"]}: {recipient["count"]} emails')
        
        # Erreurs fréquentes
        if show_errors:
            error_stats = EmailLog.get_failed_emails_by_error(days=days)
            
            if error_stats:
                self.stdout.write('\n❌ Erreurs fréquentes:')
                for error, count in list(error_stats.items())[:10]:
                    # Tronquer les messages d'erreur longs
                    error_short = error[:80] + '...' if len(error) > 80 else error
                    self.stdout.write(f'  • {count}x: {error_short}')
        
        # Tendance quotidienne (derniers 7 jours)
        self.stdout.write('\n📅 Tendance des 7 derniers jours:')
        
        for i in range(7):
            day = timezone.now().date() - timedelta(days=i)
            day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.time.min))
            day_end = timezone.make_aware(timezone.datetime.combine(day, timezone.time.max))
            
            day_logs = EmailLog.objects.filter(
                created_at__gte=day_start,
                created_at__lte=day_end
            )
            
            total = day_logs.count()
            sent = day_logs.filter(status=EmailLog.Status.SENT).count()
            
            day_name = day.strftime('%A %d/%m')
            if total > 0:
                success_rate = round((sent / total * 100), 1)
                self.stdout.write(f'  • {day_name}: {total} emails ({success_rate}% succès)')
            else:
                self.stdout.write(f'  • {day_name}: 0 email')
        
        # Recommandations
        self.stdout.write('\n💡 Recommandations:')
        
        if stats["failure_rate"] > 10:
            self.stdout.write('  ⚠️  Taux d\'échec élevé (>10%). Vérifiez la configuration SMTP.')
        
        if stats["pending"] > 0:
            self.stdout.write(f'  ⏳ {stats["pending"]} emails en attente. Vérifiez le processus d\'envoi.')
        
        if stats["success_rate"] >= 95:
            self.stdout.write('  ✅ Excellent taux de succès!')
        elif stats["success_rate"] >= 90:
            self.stdout.write('  👍 Bon taux de succès.')
        
        self.stdout.write('')


# Import nécessaire pour les annotations
from django.db import models