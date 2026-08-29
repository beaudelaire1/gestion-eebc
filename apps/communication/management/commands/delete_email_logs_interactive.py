"""
Commande de gestion pour supprimer les logs emails de manière interactive avec commit Git.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.communication.models import EmailLog
import subprocess
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Supprimer les logs emails de manière interactive avec commit Git'

    def add_arguments(self, parser):
        parser.add_argument(
            '--status',
            type=str,
            default='',
            help='Filtrer par statut (pending, sent, failed, etc.)',
        )
        parser.add_argument(
            '--older-than-days',
            type=int,
            default=0,
            help='Supprimer les logs plus anciens que X jours',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Afficher ce qui serait supprimé sans effectuer la suppression',
        )
        parser.add_argument(
            '--no-commit',
            action='store_true',
            help='Ne pas faire de commit Git après suppression',
        )

    def handle(self, *args, **options):
        """Programme principal."""
        status_filter = options.get('status', '')
        older_than_days = options.get('older_than_days', 0)
        dry_run = options.get('dry_run', False)
        no_commit = options.get('no_commit', False)

        # Récupérer les logs
        logs = EmailLog.objects.all().order_by('-created_at')

        if status_filter:
            logs = logs.filter(status=status_filter)

        if older_than_days > 0:
            cutoff_date = timezone.now() - timezone.timedelta(days=older_than_days)
            logs = logs.filter(created_at__lt=cutoff_date)

        if logs.count() == 0:
            self.stdout.write(self.style.WARNING('⚠️  Aucun log à afficher.'))
            return

        # Afficher les logs avec numéros
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('📧 LOGS EMAILS DISPONIBLES POUR SUPPRESSION'))
        self.stdout.write('='*80 + '\n')

        displayed_logs = []
        for idx, log in enumerate(logs[:100], 1):  # Limiter à 100 pour éviter le spam
            displayed_logs.append(log)
            
            status_colors = {
                'sent': 'green',
                'failed': 'red',
                'pending': 'yellow',
                'bounced': 'red',
                'opened': 'cyan',
                'clicked': 'blue',
            }
            
            status_display = log.get_status_display()
            color = status_colors.get(log.status, 'white')
            
            self.stdout.write(
                f"{idx:3d}. [{log.created_at.strftime('%d/%m/%Y %H:%M')}] "
                f"{log.recipient_email:30s} | Status: {status_display:10s} | {log.subject[:40]}"
            )

        self.stdout.write('\n' + '-'*80)
        self.stdout.write(f'Total: {logs.count()} logs (montrant {min(100, logs.count())})')
        self.stdout.write('-'*80 + '\n')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 Mode dry-run: aucune suppression.'))
            return

        # Demander quels logs supprimer
        self.stdout.write('\n📝 SÉLECTION DES LOGS À SUPPRIMER')
        self.stdout.write('-'*80)
        self.stdout.write('Exemples:')
        self.stdout.write('  • "1" pour supprimer le log #1')
        self.stdout.write('  • "1,3,5" pour supprimer les logs #1, #3, #5')
        self.stdout.write('  • "1-5" pour supprimer les logs #1 à #5')
        self.stdout.write('  • "all" pour supprimer tous les logs affichés')
        self.stdout.write('  • "quit" ou "exit" pour annuler')
        self.stdout.write('-'*80 + '\n')

        user_input = input('👉 Entrez les numéros à supprimer: ').strip().lower()

        if user_input in ['quit', 'exit', 'q']:
            self.stdout.write(self.style.WARNING('❌ Suppression annulée.'))
            return

        # Parser la sélection
        selected_indices = self._parse_selection(user_input, len(displayed_logs))

        if not selected_indices:
            self.stdout.write(self.style.WARNING('❌ Sélection invalide.'))
            return

        # Logs à supprimer
        logs_to_delete = [displayed_logs[i] for i in selected_indices]
        
        self.stdout.write('\n' + self.style.WARNING('='*80))
        self.stdout.write(self.style.WARNING('⚠️  CONFIRMATION DE SUPPRESSION'))
        self.stdout.write('='*80 + '\n')

        for idx, log in enumerate(logs_to_delete, 1):
            self.stdout.write(
                f"{idx}. {log.recipient_email} - {log.subject[:50]} "
                f"({log.get_status_display()})"
            )

        self.stdout.write('\n' + self.style.WARNING(f'Total: {len(logs_to_delete)} log(s) à supprimer'))
        self.stdout.write(self.style.WARNING('Cette action est IRRÉVERSIBLE.\n'))

        confirm = input('❓ Êtes-vous sûr? (oui/non): ').strip().lower()
        if confirm not in ['oui', 'o', 'yes', 'y']:
            self.stdout.write(self.style.WARNING('❌ Suppression annulée.'))
            return

        # Supprimer
        ids_to_delete = [log.id for log in logs_to_delete]
        deleted_count = EmailLog.objects.filter(id__in=ids_to_delete).delete()[0]

        self.stdout.write('\n' + self.style.SUCCESS('='*80))
        self.stdout.write(self.style.SUCCESS(f'✅ {deleted_count} log(s) supprimé(s) avec succès!'))
        self.stdout.write('='*80 + '\n')

        # Statistiques post-suppression
        new_count = EmailLog.objects.count()
        self.stdout.write(f'📊 Logs restants: {new_count}')
        self.stdout.write(f'   • Total avant: {new_count + deleted_count}')
        self.stdout.write(f'   • Supprimés: {deleted_count}')
        self.stdout.write(f'   • Restants: {new_count}\n')

        # Commit Git
        if not no_commit:
            self._make_git_commit(deleted_count, ids_to_delete)

        self.stdout.write(self.style.SUCCESS('✨ Opération terminée!\n'))

    def _parse_selection(self, user_input, total_items):
        """Parse la sélection utilisateur."""
        indices = set()

        if user_input == 'all':
            return list(range(total_items))

        parts = user_input.split(',')
        for part in parts:
            part = part.strip()
            
            if '-' in part:
                # Range: "1-5"
                try:
                    start, end = part.split('-')
                    start = int(start.strip()) - 1
                    end = int(end.strip())
                    if 0 <= start < total_items and 0 < end <= total_items:
                        indices.update(range(start, end))
                except (ValueError, IndexError):
                    pass
            else:
                # Single: "1"
                try:
                    idx = int(part) - 1
                    if 0 <= idx < total_items:
                        indices.add(idx)
                except ValueError:
                    pass

        return sorted(list(indices))

    def _make_git_commit(self, deleted_count, ids_to_delete):
        """Fait un commit Git pour tracer les suppressions."""
        try:
            # Préparer le message de commit
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            commit_message = (
                f"[MAINTENANCE] Suppression de {deleted_count} logs emails\n\n"
                f"Date: {timestamp}\n"
                f"IDs supprimés: {', '.join(map(str, ids_to_delete[:10]))}"
                f"{'...' if len(ids_to_delete) > 10 else ''}\n"
                f"Total: {deleted_count} logs"
            )

            # Créer un fichier de tracking
            tracking_file = 'logs/email_deletions.log'
            try:
                with open(tracking_file, 'a') as f:
                    f.write(f"\n[{timestamp}] Supprimés {deleted_count} logs (IDs: {ids_to_delete})\n")
            except Exception:
                pass

            # Faire le commit Git
            subprocess.run(
                ['git', 'add', '-A'],
                capture_output=True,
                timeout=10
            )
            
            result = subprocess.run(
                ['git', 'commit', '-m', commit_message],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Commit Git créé: {deleted_count} logs suppressions tracées')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  Commit Git échoué (repository peut être clean)')
                )

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Erreur lors du commit Git: {str(e)}')
            )
