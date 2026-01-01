"""
Tâches Celery pour le module Communication.

Ces tâches sont exécutées de manière asynchrone ou planifiée.
"""

from celery import shared_task


@shared_task
def weekly_visit_reminder_task():
    """
    Tâche hebdomadaire : Rappel des membres non visités depuis 6 mois.
    
    Planification recommandée : Tous les lundis à 8h
    Configurer dans gestion_eebc/celery.py avec Celery Beat.
    """
    from apps.communication.signals import send_weekly_visit_reminder
    send_weekly_visit_reminder()
    return "Rappel hebdomadaire envoyé"


@shared_task
def send_event_notifications_task():
    """
    Tâche quotidienne : Envoie les notifications pour les événements à venir.
    
    Vérifie les événements dont la date de notification est atteinte
    et envoie les rappels aux destinataires concernés.
    """
    from datetime import date
    from apps.events.models import Event
    from apps.communication.models import Notification
    
    today = date.today()
    
    # Événements à notifier (date - notify_before jours = aujourd'hui)
    events_to_notify = Event.objects.filter(
        notification_sent=False,
        is_cancelled=False,
        start_date__gte=today
    )
    
    notified_count = 0
    
    for event in events_to_notify:
        # Calculer si c'est le moment de notifier
        from datetime import timedelta
        notify_date = event.start_date - timedelta(days=event.notify_before)
        
        if notify_date <= today:
            recipients = event.get_notification_recipients()
            
            for email in recipients:
                # Trouver l'utilisateur correspondant
                from apps.accounts.models import User
                user = User.objects.filter(email=email).first()
                
                if user:
                    Notification.objects.create(
                        recipient=user,
                        title=f"📅 Rappel : {event.title}",
                        message=f"L'événement '{event.title}' aura lieu le {event.start_date.strftime('%d/%m/%Y')}.",
                        notification_type='event',
                        link=f"/events/{event.pk}/"
                    )
            
            event.notification_sent = True
            event.save(update_fields=['notification_sent'])
            notified_count += 1
    
    return f"{notified_count} événement(s) notifié(s)"


@shared_task
def cleanup_old_notifications_task():
    """
    Tâche mensuelle : Nettoie les anciennes notifications lues.
    
    Supprime les notifications lues depuis plus de 90 jours.
    """
    from datetime import timedelta
    from django.utils import timezone
    from apps.communication.models import Notification
    
    cutoff_date = timezone.now() - timedelta(days=90)
    
    deleted_count, _ = Notification.objects.filter(
        is_read=True,
        read_at__lt=cutoff_date
    ).delete()
    
    return f"{deleted_count} notification(s) supprimée(s)"
