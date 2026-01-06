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
    # =========================================================================
    # NOTIFICATIONS D'ÉVÉNEMENTS
    # =========================================================================
    
    # Vérifier les événements à notifier tous les jours à 8h
    'check-event-notifications-daily': {
        'task': 'apps.events.tasks.send_event_notifications',
        'schedule': crontab(hour=8, minute=0),
    },
    
    # Rappels d'événements
    'send-event-reminders': {
        'task': 'apps.communication.tasks.send_event_reminders',
        'schedule': crontab(hour=7, minute=0),
    },
    
    # =========================================================================
    # NOTIFICATIONS MEMBRES
    # =========================================================================
    
    # Vœux d'anniversaire tous les jours à 8h
    'send-birthday-wishes': {
        'task': 'apps.communication.tasks.send_birthday_notifications',
        'schedule': crontab(hour=8, minute=0),
    },
    
    # Vérification des absences tous les lundis à 9h
    'check-member-absences': {
        'task': 'apps.communication.tasks.check_member_absences',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
    },
    
    # =========================================================================
    # WORSHIP - PLANIFICATION DES CULTES
    # =========================================================================
    
    # Envoi des notifications de culte tous les jours à 9h
    'send-worship-notifications': {
        'task': 'apps.worship.tasks.send_scheduled_notifications',
        'schedule': crontab(hour=9, minute=0),
    },
    
    # =========================================================================
    # FINANCE
    # =========================================================================
    
    # Génération des reçus fiscaux le 15 janvier à 10h
    'generate-annual-tax-receipts': {
        'task': 'apps.communication.tasks.generate_annual_tax_receipts',
        'schedule': crontab(hour=10, minute=0, day_of_month=15, month_of_year=1),
    },
    
    # Envoi des reçus fiscaux par email le 20 janvier à 10h
    'send-tax-receipts-batch': {
        'task': 'apps.communication.tasks.send_donation_receipts_batch',
        'schedule': crontab(hour=10, minute=0, day_of_month=20, month_of_year=1),
    },
    
    # =========================================================================
    # MAINTENANCE
    # =========================================================================
    
    # Nettoyage des logs le 1er de chaque mois à 3h
    'cleanup-old-logs': {
        'task': 'apps.communication.tasks.cleanup_old_logs',
        'schedule': crontab(hour=3, minute=0, day_of_month=1),
    },
}

app.conf.timezone = 'America/Cayenne'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

