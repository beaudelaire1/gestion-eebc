# Configuration Celery & Redis pour Gestion EEBC

Ce guide explique comment configurer et lancer Celery avec Redis pour les tâches asynchrones.

## Prérequis

- Python 3.11+
- Redis Server

## Installation de Redis

### Windows

1. **Option 1 : WSL (recommandé)**
   ```bash
   # Dans WSL Ubuntu
   sudo apt update
   sudo apt install redis-server
   sudo service redis-server start
   ```

2. **Option 2 : Memurai (alternative Windows native)**
   - Télécharger depuis https://www.memurai.com/
   - Installer et démarrer le service

3. **Option 3 : Docker**
   ```bash
   docker run -d -p 6379:6379 --name redis redis:alpine
   ```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### macOS
```bash
brew install redis
brew services start redis
```

## Vérifier que Redis fonctionne

```bash
redis-cli ping
# Doit répondre: PONG
```

## Configuration Django

La configuration est déjà en place dans `gestion_eebc/settings.py` :

```python
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
```

Pour personnaliser, ajoutez dans `.env` :
```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Lancer Celery

### Terminal 1 : Worker Celery
```bash
# Activer l'environnement virtuel
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Lancer le worker
celery -A gestion_eebc worker -l INFO
```

### Terminal 2 : Celery Beat (tâches planifiées)
```bash
celery -A gestion_eebc beat -l INFO
```

### Alternative : Worker + Beat ensemble (développement)
```bash
celery -A gestion_eebc worker -B -l INFO
```

## Tâches planifiées configurées

| Tâche | Fréquence | Description |
|-------|-----------|-------------|
| `send_event_notifications` | Tous les jours 8h | Notifications d'événements |
| `send_event_reminders` | Tous les jours 7h | Rappels d'événements |
| `send_birthday_notifications` | Tous les jours 8h | Vœux d'anniversaire |
| `check_member_absences` | Lundi 9h | Vérification des absences |
| `send_worship_notifications` | Tous les jours 9h | Notifications de culte |
| `generate_annual_tax_receipts` | 15 janvier 10h | Génération reçus fiscaux |
| `send_donation_receipts_batch` | 20 janvier 10h | Envoi reçus fiscaux |
| `cleanup_old_logs` | 1er du mois 3h | Nettoyage des logs |

## Tester une tâche manuellement

```python
# Dans le shell Django
python manage.py shell

from apps.communication.tasks import send_birthday_notifications
result = send_birthday_notifications.delay()
print(result.get())  # Attendre le résultat
```

## Monitoring (optionnel)

### Flower - Interface web pour Celery
```bash
pip install flower
celery -A gestion_eebc flower --port=5555
```
Accéder à http://localhost:5555

## Production

Pour la production, utilisez un gestionnaire de processus comme Supervisor ou systemd.

### Exemple Supervisor (`/etc/supervisor/conf.d/celery.conf`)
```ini
[program:celery-worker]
command=/path/to/venv/bin/celery -A gestion_eebc worker -l INFO
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker_error.log

[program:celery-beat]
command=/path/to/venv/bin/celery -A gestion_eebc beat -l INFO
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat_error.log
```

## Dépannage

### Erreur de connexion Redis
```
Error: Connection refused
```
→ Vérifier que Redis est démarré : `redis-cli ping`

### Worker ne reçoit pas les tâches
→ Vérifier que le broker URL est correct
→ Vérifier les logs du worker

### Tâches en attente mais non exécutées
→ Vérifier que le worker est bien lancé
→ Vérifier la queue : `celery -A gestion_eebc inspect active`
