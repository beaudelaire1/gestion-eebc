"""
Tâches Celery pour le module Worship.

Gère l'envoi automatique des notifications aux participants des cultes.
"""
from celery import shared_task
from django.utils import timezone
from datetime import date


@shared_task
def send_scheduled_notifications():
    """
    Envoie les notifications programmées pour aujourd'hui.
    
    Cette tâche doit être exécutée quotidiennement (via Celery Beat).
    Elle vérifie les notifications en attente dont la date d'envoi
    est aujourd'hui et les envoie.
    """
    from apps.worship.models import ServiceNotification
    
    today = date.today()
    
    notifications = ServiceNotification.objects.filter(
        status='pending',
        scheduled_date__lte=today
    )
    
    sent_count = 0
    error_count = 0
    
    for notification in notifications:
        try:
            notification.send()
            if notification.status == 'sent':
                sent_count += 1
            else:
                error_count += 1
        except Exception as e:
            notification.status = 'failed'
            notification.error_message = str(e)
            notification.save()
            error_count += 1
    
    return {
        'sent': sent_count,
        'errors': error_count,
        'date': str(today)
    }


@shared_task
def send_service_reminder(service_id):
    """
    Envoie un rappel pour un culte spécifique.
    
    Args:
        service_id: ID du ScheduledService
    """
    from apps.worship.models import ScheduledService
    
    try:
        service = ScheduledService.objects.get(id=service_id)
        service.send_notifications()
        return {'success': True, 'service': str(service)}
    except ScheduledService.DoesNotExist:
        return {'success': False, 'error': 'Service not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@shared_task
def generate_monthly_schedule(site_id, year, month):
    """
    Génère automatiquement un planning mensuel avec tous les dimanches.
    
    Args:
        site_id: ID du site
        year: Année
        month: Mois (1-12)
    """
    from apps.worship.models import MonthlySchedule, ScheduledService
    from apps.core.models import Site
    
    try:
        site = Site.objects.get(id=site_id)
        
        schedule, created = MonthlySchedule.objects.get_or_create(
            year=year,
            month=month,
            site=site,
            defaults={'status': 'brouillon'}
        )
        
        if created:
            # Générer les dimanches
            sundays = schedule.get_sundays()
            for sunday in sundays:
                ScheduledService.objects.get_or_create(
                    schedule=schedule,
                    date=sunday,
                    defaults={'start_time': '09:30'}
                )
        
        return {
            'success': True,
            'schedule_id': schedule.id,
            'created': created,
            'sundays': len(schedule.get_sundays())
        }
    
    except Exception as e:
        return {'success': False, 'error': str(e)}
