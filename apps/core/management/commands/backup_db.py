"""
Commande de backup de la base de données.
Fonctionne sans Celery — peut être lancée via cron Render.

Usage:
    python manage.py backup_db
    python manage.py backup_db --type manual
"""
import os
import subprocess
import logging
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sauvegarde la base de données (PostgreSQL ou SQLite)'

    def add_arguments(self, parser):
        parser.add_argument('--type', default='automatic', choices=['automatic', 'manual'])

    def handle(self, *args, **options):
        from apps.core.models import DatabaseBackup

        backup_dir = Path(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_config = settings.DATABASES['default']
        db_engine = db_config['ENGINE']

        if 'sqlite' in db_engine:
            filename = f'backup_{timestamp}.sqlite3'
            engine_name = 'SQLite'
        else:
            filename = f'backup_{timestamp}.sql'
            engine_name = 'PostgreSQL' if 'postgresql' in db_engine else 'MySQL'

        backup_path = backup_dir / filename

        record = DatabaseBackup.create_backup_record(
            filename=filename,
            file_path=str(backup_path),
            backup_type=options['type'],
            database_engine=engine_name,
        )

        try:
            if 'sqlite' in db_engine:
                import shutil
                shutil.copy2(db_config['NAME'], backup_path)

            elif 'postgresql' in db_engine:
                cmd = [
                    'pg_dump',
                    '--host', db_config.get('HOST', 'localhost'),
                    '--port', str(db_config.get('PORT', 5432)),
                    '--username', db_config['USER'],
                    '--dbname', db_config['NAME'],
                    '--file', str(backup_path),
                    '--no-password',
                ]
                env = os.environ.copy()
                env['PGPASSWORD'] = db_config['PASSWORD']
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"pg_dump error: {result.stderr}")
            else:
                raise Exception(f"Moteur non supporté: {db_engine}")

            size = backup_path.stat().st_size
            if size == 0:
                raise Exception("Fichier de sauvegarde vide")

            record.mark_as_success(file_size=size)
            size_mb = size / (1024 * 1024)
            self.stdout.write(self.style.SUCCESS(f'✓ Backup créé: {filename} ({size_mb:.2f} MB)'))

            # Rotation : garder les 30 dernières
            backups = sorted(backup_dir.glob('backup_*'), key=lambda f: f.stat().st_mtime, reverse=True)
            for old in backups[30:]:
                old.unlink()
                self.stdout.write(f'  Ancien backup supprimé: {old.name}')

            DatabaseBackup.cleanup_old_records(keep_count=30)

        except Exception as e:
            record.mark_as_failed(error_message=str(e))
            self.stderr.write(self.style.ERROR(f'✗ Backup échoué: {e}'))
            logger.error(f"Backup failed: {e}", exc_info=True)

            # Alerte email
            try:
                from django.core.mail import mail_admins
                mail_admins(
                    subject="[EEBC] Échec backup automatique",
                    message=f"Erreur: {e}\nHeure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    fail_silently=True,
                )
            except Exception:
                pass
