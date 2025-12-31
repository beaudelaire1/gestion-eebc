"""
Configuration Celery pour Gestion EEBC.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Définir le module de paramètres par défaut
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')

app = Celery('gestion_eebc')

# Utiliser les paramètres Django avec le préfixe CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découverte automatique des tâches dans les apps installées
app.autodiscover_tasks()

# Configuration du beat schedule (tâches planifiées)
app.conf.beat_schedule = {
    # Vérifier les événements à notifier tous les jours à 8h
    'check-event-notifications-daily': {
        'task': 'apps.events.tasks.send_event_notifications',
        'schedule': crontab(hour=8, minute=0),
    },
    # Rappel le matin même de l'événement à 7h
    'send-event-reminders-morning': {
        'task': 'apps.events.tasks.send_event_reminders',
        'schedule': crontab(hour=7, minute=0),
    },
}

app.conf.timezone = 'America/Cayenne'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

