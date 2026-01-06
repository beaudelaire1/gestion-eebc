"""
Tâches Celery pour l'application core.
"""
import os
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path
from django.conf import settings
from django.core.mail import mail_admins
from celery import shared_task
from django.db import connection

logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=True)
def backup_database_task(self):
    """
    Tâche Celery pour effectuer une sauvegarde quotidienne de la base de données.
    
    Cette tâche:
    1. Crée une sauvegarde de la base de données
    2. Gère la rotation des sauvegardes (garde les 30 dernières)
    3. Envoie une alerte en cas d'échec
    4. Enregistre la sauvegarde dans le modèle DatabaseBackup
    
    Requirements: 18.1, 18.2, 18.4
    """
    from apps.core.models import DatabaseBackup
    
    # Créer un enregistrement de sauvegarde
    backup_record = None
    
    try:
        logger.info("Début de la sauvegarde de la base de données")
        
        # Créer le répertoire de sauvegarde s'il n'existe pas
        backup_dir = Path(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        # Générer le nom du fichier de sauvegarde avec timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Obtenir la configuration de la base de données
        db_config = settings.DATABASES['default']
        db_engine = db_config['ENGINE']
        
        # Déterminer le type de fichier selon le moteur
        if db_engine == 'django.db.backends.sqlite3':
            backup_filename = f'backup_{timestamp}.sqlite3'
            backup_path = backup_dir / backup_filename
            engine_name = 'SQLite'
        else:
            backup_filename = f'backup_{timestamp}.sql'
            backup_path = backup_dir / backup_filename
            if 'postgresql' in db_engine:
                engine_name = 'PostgreSQL'
            elif 'mysql' in db_engine:
                engine_name = 'MySQL'
            else:
                engine_name = 'Unknown'
        
        # Créer l'enregistrement de sauvegarde
        backup_record = DatabaseBackup.create_backup_record(
            filename=backup_filename,
            file_path=str(backup_path),
            backup_type='automatic',
            celery_task_id=self.request.id,
            database_engine=engine_name
        )
        
        # Effectuer la sauvegarde selon le type de base de données
        if db_engine == 'django.db.backends.sqlite3':
            # Pour SQLite, copier le fichier de base de données
            import shutil
            db_path = db_config['NAME']
            shutil.copy2(db_path, backup_path)
            logger.info(f"Sauvegarde SQLite créée: {backup_path}")
            
        elif db_engine == 'django.db.backends.postgresql':
            # Pour PostgreSQL, utiliser pg_dump
            cmd = [
                'pg_dump',
                '--host', db_config.get('HOST', 'localhost'),
                '--port', str(db_config.get('PORT', 5432)),
                '--username', db_config['USER'],
                '--dbname', db_config['NAME'],
                '--file', str(backup_path),
                '--verbose',
                '--no-password'
            ]
            
            # Définir le mot de passe via variable d'environnement
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Erreur pg_dump: {result.stderr}")
                
            logger.info(f"Sauvegarde PostgreSQL créée: {backup_path}")
            
        elif db_engine == 'django.db.backends.mysql':
            # Pour MySQL, utiliser mysqldump
            cmd = [
                'mysqldump',
                '--host', db_config.get('HOST', 'localhost'),
                '--port', str(db_config.get('PORT', 3306)),
                '--user', db_config['USER'],
                f'--password={db_config["PASSWORD"]}',
                '--single-transaction',
                '--routines',
                '--triggers',
                db_config['NAME']
            ]
            
            with open(backup_path, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                
            if result.returncode != 0:
                raise Exception(f"Erreur mysqldump: {result.stderr}")
                
            logger.info(f"Sauvegarde MySQL créée: {backup_path}")
            
        else:
            raise Exception(f"Type de base de données non supporté: {db_engine}")
        
        # Vérifier la taille du fichier de sauvegarde
        backup_size = backup_path.stat().st_size
            
        if backup_size == 0:
            raise Exception("Le fichier de sauvegarde est vide")
        
        # Marquer la sauvegarde comme réussie
        backup_record.mark_as_success(file_size=backup_size)
        
        # Effectuer la rotation des sauvegardes (garder les 30 dernières)
        _cleanup_old_backups(backup_dir)
        
        # Nettoyer les anciens enregistrements de sauvegarde
        DatabaseBackup.cleanup_old_records(keep_count=30)
        
        # Convertir la taille en MB pour le log
        size_mb = backup_size / (1024 * 1024)
        
        logger.info(f"Sauvegarde terminée avec succès. Taille: {size_mb:.2f} MB")
        
        return {
            'success': True,
            'backup_file': str(backup_path),
            'size_bytes': backup_size,
            'message': f'Sauvegarde créée avec succès ({size_mb:.2f} MB)'
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de la sauvegarde de la base de données: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Marquer la sauvegarde comme échouée
        if backup_record:
            backup_record.mark_as_failed(error_message=str(e))
        
        # Envoyer une alerte par email aux administrateurs
        try:
            mail_admins(
                subject="[EEBC] Échec de la sauvegarde automatique",
                message=f"""
Une erreur s'est produite lors de la sauvegarde automatique de la base de données.

Erreur: {str(e)}

Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Veuillez vérifier la configuration et relancer la sauvegarde manuellement si nécessaire.
                """.strip(),
                fail_silently=False
            )
            logger.info("Email d'alerte envoyé aux administrateurs")
        except Exception as mail_error:
            logger.error(f"Impossible d'envoyer l'email d'alerte: {mail_error}")
        
        # Re-lever l'exception pour que Celery marque la tâche comme échouée
        raise self.retry(exc=e, countdown=60, max_retries=3)


def _cleanup_old_backups(backup_dir: Path, keep_count: int = 30):
    """
    Supprime les anciennes sauvegardes, en gardant les 'keep_count' plus récentes.
    
    Args:
        backup_dir: Répertoire contenant les sauvegardes
        keep_count: Nombre de sauvegardes à conserver (défaut: 30)
    
    Requirements: 18.2
    """
    try:
        # Lister tous les fichiers de sauvegarde
        backup_files = []
        
        # Chercher les fichiers .sql et .sqlite3
        for pattern in ['backup_*.sql', 'backup_*.sqlite3']:
            backup_files.extend(backup_dir.glob(pattern))
        
        if len(backup_files) <= keep_count:
            logger.info(f"Nombre de sauvegardes ({len(backup_files)}) <= limite ({keep_count}), aucune suppression nécessaire")
            return
        
        # Trier par date de modification (plus récent en premier)
        backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Supprimer les fichiers les plus anciens
        files_to_delete = backup_files[keep_count:]
        
        for file_path in files_to_delete:
            try:
                file_path.unlink()
                logger.info(f"Ancienne sauvegarde supprimée: {file_path.name}")
            except Exception as e:
                logger.warning(f"Impossible de supprimer {file_path.name}: {e}")
        
        logger.info(f"Rotation des sauvegardes terminée. {len(files_to_delete)} fichiers supprimés, {keep_count} conservés")
        
    except Exception as e:
        logger.error(f"Erreur lors de la rotation des sauvegardes: {e}")


@shared_task(bind=True, ignore_result=True)
def manual_backup_task(self, user_id=None):
    """
    Tâche pour effectuer une sauvegarde manuelle (déclenchée par un utilisateur).
    
    Args:
        user_id: ID de l'utilisateur qui a déclenché la sauvegarde
    
    Returns:
        dict: Résultat de la sauvegarde
    """
    from apps.core.models import DatabaseBackup
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        logger.info(f"Sauvegarde manuelle déclenchée par l'utilisateur {user_id}")
        
        # Récupérer l'utilisateur
        created_by = None
        if user_id:
            try:
                created_by = User.objects.get(id=user_id)
            except User.DoesNotExist:
                logger.warning(f"Utilisateur {user_id} non trouvé")
        
        # Créer le répertoire de sauvegarde s'il n'existe pas
        backup_dir = Path(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        # Générer le nom du fichier de sauvegarde avec timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Obtenir la configuration de la base de données
        db_config = settings.DATABASES['default']
        db_engine = db_config['ENGINE']
        
        # Déterminer le type de fichier selon le moteur
        if db_engine == 'django.db.backends.sqlite3':
            backup_filename = f'manual_backup_{timestamp}.sqlite3'
            backup_path = backup_dir / backup_filename
            engine_name = 'SQLite'
        else:
            backup_filename = f'manual_backup_{timestamp}.sql'
            backup_path = backup_dir / backup_filename
            if 'postgresql' in db_engine:
                engine_name = 'PostgreSQL'
            elif 'mysql' in db_engine:
                engine_name = 'MySQL'
            else:
                engine_name = 'Unknown'
        
        # Créer l'enregistrement de sauvegarde
        backup_record = DatabaseBackup.create_backup_record(
            filename=backup_filename,
            file_path=str(backup_path),
            backup_type='manual',
            created_by=created_by,
            celery_task_id=self.request.id,
            database_engine=engine_name
        )
        
        # Utiliser la même logique que la sauvegarde automatique
        # Effectuer la sauvegarde selon le type de base de données
        if db_engine == 'django.db.backends.sqlite3':
            # Pour SQLite, copier le fichier de base de données
            import shutil
            db_path = db_config['NAME']
            shutil.copy2(db_path, backup_path)
            logger.info(f"Sauvegarde SQLite manuelle créée: {backup_path}")
            
        elif db_engine == 'django.db.backends.postgresql':
            # Pour PostgreSQL, utiliser pg_dump
            cmd = [
                'pg_dump',
                '--host', db_config.get('HOST', 'localhost'),
                '--port', str(db_config.get('PORT', 5432)),
                '--username', db_config['USER'],
                '--dbname', db_config['NAME'],
                '--file', str(backup_path),
                '--verbose',
                '--no-password'
            ]
            
            # Définir le mot de passe via variable d'environnement
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Erreur pg_dump: {result.stderr}")
                
            logger.info(f"Sauvegarde PostgreSQL manuelle créée: {backup_path}")
            
        elif db_engine == 'django.db.backends.mysql':
            # Pour MySQL, utiliser mysqldump
            cmd = [
                'mysqldump',
                '--host', db_config.get('HOST', 'localhost'),
                '--port', str(db_config.get('PORT', 3306)),
                '--user', db_config['USER'],
                f'--password={db_config["PASSWORD"]}',
                '--single-transaction',
                '--routines',
                '--triggers',
                db_config['NAME']
            ]
            
            with open(backup_path, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                
            if result.returncode != 0:
                raise Exception(f"Erreur mysqldump: {result.stderr}")
                
            logger.info(f"Sauvegarde MySQL manuelle créée: {backup_path}")
            
        else:
            raise Exception(f"Type de base de données non supporté: {db_engine}")
        
        # Vérifier la taille du fichier de sauvegarde
        backup_size = backup_path.stat().st_size
            
        if backup_size == 0:
            raise Exception("Le fichier de sauvegarde est vide")
        
        # Marquer la sauvegarde comme réussie
        backup_record.mark_as_success(file_size=backup_size)
        
        # Convertir la taille en MB pour le log
        size_mb = backup_size / (1024 * 1024)
        
        logger.info(f"Sauvegarde manuelle terminée avec succès. Taille: {size_mb:.2f} MB")
        
        return {
            'success': True,
            'backup_file': str(backup_path),
            'size_bytes': backup_size,
            'message': f'Sauvegarde manuelle créée avec succès ({size_mb:.2f} MB)',
            'backup_id': backup_record.id
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde manuelle: {e}")
        
        # Marquer la sauvegarde comme échouée si l'enregistrement existe
        if 'backup_record' in locals():
            backup_record.mark_as_failed(error_message=str(e))
        
        raise


@shared_task(bind=True, ignore_result=True)
def cleanup_backup_directory(self):
    """
    Tâche de maintenance pour nettoyer le répertoire de sauvegarde.
    Supprime les fichiers corrompus ou partiels.
    """
    try:
        backup_dir = Path(settings.BASE_DIR) / 'backups'
        
        if not backup_dir.exists():
            logger.info("Répertoire de sauvegarde inexistant, aucun nettoyage nécessaire")
            return
        
        cleaned_files = 0
        
        # Vérifier tous les fichiers de sauvegarde
        for backup_file in backup_dir.glob('backup_*'):
            try:
                # Vérifier si le fichier est vide ou très petit (probablement corrompu)
                if backup_file.stat().st_size < 1024:  # Moins de 1KB
                    backup_file.unlink()
                    logger.warning(f"Fichier de sauvegarde corrompu supprimé: {backup_file.name}")
                    cleaned_files += 1
                    
            except Exception as e:
                logger.error(f"Erreur lors de la vérification de {backup_file.name}: {e}")
        
        logger.info(f"Nettoyage terminé. {cleaned_files} fichiers corrompus supprimés")
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage du répertoire de sauvegarde: {e}")