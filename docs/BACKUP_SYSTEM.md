# Système de Sauvegarde Automatique

Ce document décrit le système de sauvegarde automatique de la base de données implémenté dans Gestion EEBC.

## Fonctionnalités

### 1. Sauvegarde Automatique Quotidienne

- **Planification**: Tous les jours à 2h du matin
- **Tâche Celery**: `apps.core.tasks.backup_database_task`
- **Configuration**: Définie dans `gestion_eebc/celery.py`

### 2. Rotation des Sauvegardes

- **Rétention**: Les 30 dernières sauvegardes sont conservées
- **Nettoyage automatique**: Les anciennes sauvegardes sont supprimées automatiquement
- **Nettoyage du répertoire**: Chaque dimanche à 1h du matin

### 3. Gestion via l'Interface Admin

- **Accès**: `/admin/core/databasebackup/`
- **Fonctionnalités**:
  - Lister toutes les sauvegardes
  - Télécharger les sauvegardes réussies
  - Déclencher une sauvegarde manuelle
  - Voir le statut et les détails de chaque sauvegarde

### 4. Alertes en Cas d'Échec

- **Email automatique**: Envoyé aux administrateurs en cas d'échec
- **Retry automatique**: 3 tentatives avec délai de 60 secondes
- **Logging**: Tous les événements sont loggés

## Types de Base de Données Supportés

### SQLite (par défaut)
- **Méthode**: Copie directe du fichier de base de données
- **Format**: `.sqlite3`

### PostgreSQL
- **Méthode**: `pg_dump`
- **Format**: `.sql`
- **Prérequis**: `pg_dump` doit être installé et accessible

### MySQL
- **Méthode**: `mysqldump`
- **Format**: `.sql`
- **Prérequis**: `mysqldump` doit être installé et accessible

## Configuration

### Variables d'Environnement

Aucune configuration spéciale n'est requise. Le système utilise automatiquement la configuration de base de données définie dans `DATABASES['default']`.

### Répertoire de Sauvegarde

- **Emplacement**: `{BASE_DIR}/backups/`
- **Création automatique**: Le répertoire est créé automatiquement s'il n'existe pas

## Utilisation

### Sauvegarde Manuelle

1. Accéder à l'interface admin: `/admin/core/databasebackup/`
2. Cliquer sur "Créer une sauvegarde manuelle" (bouton en haut de la liste)
3. La sauvegarde sera traitée en arrière-plan via Celery
4. Actualiser la page pour voir le résultat

### Téléchargement d'une Sauvegarde

1. Dans la liste des sauvegardes, cliquer sur "Télécharger" pour une sauvegarde réussie
2. Le fichier sera téléchargé directement

### Surveillance

- **Logs**: Vérifier les logs Celery pour les détails d'exécution
- **Emails**: Les administrateurs reçoivent un email en cas d'échec
- **Interface admin**: Statut visible en temps réel

## Dépannage

### Problèmes Courants

1. **Tâche Celery non exécutée**
   - Vérifier que Celery Worker est en cours d'exécution
   - Vérifier que Celery Beat est configuré pour les tâches planifiées

2. **Erreur de permissions**
   - Vérifier les permissions d'écriture sur le répertoire `backups/`
   - Vérifier les permissions de lecture sur le fichier de base de données

3. **Outils de sauvegarde manquants**
   - Pour PostgreSQL: installer `postgresql-client`
   - Pour MySQL: installer `mysql-client`

4. **Fichier de sauvegarde vide**
   - Vérifier la configuration de la base de données
   - Vérifier les logs pour les erreurs détaillées

### Commandes de Diagnostic

```bash
# Tester la tâche de sauvegarde manuellement
python manage.py shell -c "from apps.core.tasks import backup_database_task; backup_database_task.delay()"

# Vérifier les sauvegardes existantes
python manage.py shell -c "from apps.core.models import DatabaseBackup; print(DatabaseBackup.objects.all())"

# Nettoyer les anciennes sauvegardes manuellement
python manage.py shell -c "from apps.core.models import DatabaseBackup; DatabaseBackup.cleanup_old_records()"
```

## Sécurité

- **Accès restreint**: Seuls les administrateurs peuvent accéder aux sauvegardes
- **Fichiers protégés**: Les sauvegardes sont stockées en dehors du répertoire web
- **Audit**: Toutes les actions de sauvegarde sont tracées dans les logs d'audit

## Restauration

Pour restaurer une sauvegarde:

### SQLite
```bash
# Arrêter l'application
# Remplacer le fichier de base de données
cp backups/backup_YYYYMMDD_HHMMSS.sqlite3 db.sqlite3
# Redémarrer l'application
```

### PostgreSQL
```bash
# Créer une nouvelle base de données
createdb nouvelle_db
# Restaurer la sauvegarde
psql nouvelle_db < backups/backup_YYYYMMDD_HHMMSS.sql
```

### MySQL
```bash
# Créer une nouvelle base de données
mysql -e "CREATE DATABASE nouvelle_db;"
# Restaurer la sauvegarde
mysql nouvelle_db < backups/backup_YYYYMMDD_HHMMSS.sql
```

## Monitoring

### Métriques Importantes

- **Fréquence des sauvegardes**: Quotidienne
- **Taille des sauvegardes**: Surveillée et loggée
- **Taux de succès**: Doit être proche de 100%
- **Temps d'exécution**: Surveillé via les logs Celery

### Alertes Recommandées

- Échec de sauvegarde pendant 2 jours consécutifs
- Taille de sauvegarde anormalement petite (< 1MB)
- Espace disque insuffisant dans le répertoire de sauvegarde