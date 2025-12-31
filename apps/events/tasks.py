"""
Tâches Celery pour les notifications d'événements.
"""
from celery import shared_task
from django.core.mail import send_mail, send_mass_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_event_notification_email(self, event_id, recipient_emails):
    """
    Envoie une notification email pour un événement à une liste de destinataires.
    """
    from apps.events.models import Event
    
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        logger.error(f"Event {event_id} not found")
        return
    
    if not recipient_emails:
        logger.info(f"No recipients for event {event_id}")
        return
    
    # Préparer le contenu de l'email
    subject = f"📅 Événement à venir : {event.title}"
    
    context = {
        'event': event,
        'days_until': (event.start_date - date.today()).days,
    }
    
    html_message = render_to_string('events/email/event_notification.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        # Envoyer l'email à chaque destinataire
        for email in recipient_emails:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
        
        # Marquer l'événement comme notifié
        event.notification_sent = True
        event.save(update_fields=['notification_sent'])
        
        logger.info(f"Notifications sent for event {event_id} to {len(recipient_emails)} recipients")
        return f"Sent to {len(recipient_emails)} recipients"
    
    except Exception as exc:
        logger.error(f"Failed to send notification for event {event_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task
def send_event_notifications():
    """
    Tâche planifiée : vérifie les événements qui doivent être notifiés.
    Exécutée quotidiennement.
    """
    from apps.events.models import Event
    
    today = date.today()
    events_to_notify = []
    
    # Récupérer les événements à venir non encore notifiés
    upcoming_events = Event.objects.filter(
        start_date__gte=today,
        is_cancelled=False,
        notification_sent=False,
    ).exclude(notification_scope='none')
    
    for event in upcoming_events:
        days_until = (event.start_date - today).days
        
        # Vérifier si c'est le moment de notifier
        if days_until <= event.notify_before:
            recipients = event.get_notification_recipients()
            if recipients:
                # Lancer la tâche d'envoi
                send_event_notification_email.delay(event.id, recipients)
                events_to_notify.append(event.title)
    
    logger.info(f"Processed {len(events_to_notify)} events for notifications")
    return f"Notified: {events_to_notify}"


@shared_task
def send_event_reminders():
    """
    Tâche planifiée : envoie un rappel le jour même de l'événement.
    """
    from apps.events.models import Event
    
    today = date.today()
    
    # Événements d'aujourd'hui
    todays_events = Event.objects.filter(
        start_date=today,
        is_cancelled=False,
    ).exclude(notification_scope='none')
    
    events_reminded = []
    
    for event in todays_events:
        recipients = event.get_notification_recipients()
        if recipients:
            # Envoyer le rappel
            send_event_reminder_email.delay(event.id, recipients)
            events_reminded.append(event.title)
    
    logger.info(f"Sent reminders for {len(events_reminded)} events")
    return f"Reminded: {events_reminded}"


@shared_task(bind=True, max_retries=3)
def send_event_reminder_email(self, event_id, recipient_emails):
    """
    Envoie un rappel email le jour de l'événement.
    """
    from apps.events.models import Event
    
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        logger.error(f"Event {event_id} not found")
        return
    
    if not recipient_emails:
        return
    
    subject = f"🔔 Rappel : {event.title} - Aujourd'hui !"
    
    context = {
        'event': event,
        'is_reminder': True,
    }
    
    html_message = render_to_string('events/email/event_reminder.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        for email in recipient_emails:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
        
        logger.info(f"Reminders sent for event {event_id}")
        return f"Reminders sent to {len(recipient_emails)} recipients"
    
    except Exception as exc:
        logger.error(f"Failed to send reminder for event {event_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task
def send_immediate_notification(event_id):
    """
    Envoie une notification immédiate lors de la création/modification d'un événement.
    """
    from apps.events.models import Event
    
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        return
    
    recipients = event.get_notification_recipients()
    if recipients:
        send_event_notification_email.delay(event_id, recipients)
        return f"Immediate notification queued for {len(recipients)} recipients"
    
    return "No recipients"

