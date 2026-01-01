"""
Signaux Django pour déclencher les notifications email automatiquement.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Email admin qui reçoit une copie de tout
ADMIN_EMAIL = getattr(settings, 'ADMIN_EMAIL', None) or settings.__dict__.get('ADMIN_EMAIL')


def get_admin_email():
    """Récupère l'email admin depuis les settings ou .env"""
    import os
    return os.environ.get('ADMIN_EMAIL', '')


# =============================================================================
# SIGNAUX ÉVÉNEMENTS
# =============================================================================

@receiver(post_save, sender='events.Event')
def notify_event_created_or_updated(sender, instance, created, **kwargs):
    """
    Notifie lors de la création ou modification d'un événement.
    """
    from apps.communication.email_service import (
        send_event_scheduled, send_event_cancelled, EmailService
    )
    
    admin_email = get_admin_email()
    
    # Pour l'instant, envoyer uniquement à l'admin
    # Les emails membres ne sont pas encore configurés
    recipients = []
    if admin_email:
        recipients.append(admin_email)
    
    if not recipients:
        logger.info(f"Pas de destinataires pour l'événement: {instance.title}")
        return
    
    try:
        if instance.is_cancelled:
            # Événement annulé
            for email in recipients:
                send_event_cancelled(
                    event=instance,
                    recipient_email=email,
                    cancellation_reason=getattr(instance, '_cancellation_reason', '')
                )
            logger.info(f"Notifications d'annulation envoyées pour: {instance.title}")
        
        elif created:
            # Nouvel événement
            for email in recipients:
                send_event_scheduled(
                    event=instance,
                    recipient_email=email
                )
            logger.info(f"Notifications de création envoyées pour: {instance.title} à {len(recipients)} destinataires")
    
    except Exception as e:
        logger.error(f"Erreur envoi notification événement: {e}")


# =============================================================================
# SIGNAUX CLUB BIBLIQUE - SESSIONS
# =============================================================================

@receiver(post_save, sender='bibleclub.Session')
def notify_session_created(sender, instance, created, **kwargs):
    """
    Notifie lors de la création d'une nouvelle session.
    """
    if not created:
        return
    
    from apps.communication.email_service import EmailService
    
    admin_email = get_admin_email()
    
    # Pour l'instant, envoyer uniquement à l'admin
    if not admin_email:
        return
    
    try:
        EmailService.send(
            recipient_email=admin_email,
            subject=f"📚 Nouvelle session Club Biblique - {instance.date}",
            template_name='communication/email/session_created.html',
            context={
                'session': instance,
                'monitor': None,
            },
            recipient_name='Admin'
        )
        
        logger.info(f"Notification session envoyée pour: {instance.date}")
    
    except Exception as e:
        logger.error(f"Erreur envoi notification session: {e}")


# =============================================================================
# SIGNAUX CLUB BIBLIQUE - PRÉSENCES
# =============================================================================

@receiver(post_save, sender='bibleclub.Attendance')
def notify_attendance_recorded(sender, instance, created, **kwargs):
    """
    Notifie l'admin en cas d'absence.
    """
    from apps.communication.email_service import EmailService
    
    # Seulement pour les absences
    if instance.status not in ['absent', 'absent_notified']:
        return
    
    # Éviter de notifier plusieurs fois
    if instance.status == 'absent_notified':
        return
    
    admin_email = get_admin_email()
    if not admin_email:
        return
    
    child = instance.child
    session = instance.session
    
    try:
        # Notifier l'admin de l'absence
        EmailService.send(
            recipient_email=admin_email,
            subject=f"Absence de {child.first_name} - Club Biblique EEBC",
            template_name='communication/email/absence_notification.html',
            context={
                'child': child,
                'session': session,
                'parent_name': 'Admin',
            },
            recipient_name='Admin'
        )
        
        # Marquer comme notifié
        instance.status = 'absent_notified'
        instance.save(update_fields=['status'])
        logger.info(f"Notification absence envoyée pour: {child}")
    
    except Exception as e:
        logger.error(f"Erreur envoi notification absence: {e}")


# =============================================================================
# SIGNAUX DONATIONS
# =============================================================================

@receiver(post_save, sender='campaigns.Donation')
def notify_donation_received(sender, instance, created, **kwargs):
    """
    Notifie l'admin lors d'un nouveau don.
    """
    if not created:
        return
    
    from apps.communication.email_service import send_campaign_notification
    
    admin_email = get_admin_email()
    if not admin_email:
        return
    
    try:
        send_campaign_notification(
            campaign=instance.campaign,
            donation=instance,
            donor_email=admin_email,
            donor_name=instance.donor_name or 'Anonyme'
        )
        logger.info(f"Notification don envoyée: {instance.amount}€")
    except Exception as e:
        logger.error(f"Erreur envoi notification don: {e}")


# =============================================================================
# SIGNAUX UTILISATEURS
# =============================================================================

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def notify_user_created(sender, instance, created, **kwargs):
    """
    Envoie un email de bienvenue aux nouveaux utilisateurs.
    """
    if not created or not instance.email:
        return
    
    from apps.communication.email_service import send_welcome_email
    
    try:
        send_welcome_email(instance)
        logger.info(f"Email de bienvenue envoyé à: {instance.email}")
    except Exception as e:
        logger.error(f"Erreur envoi email bienvenue: {e}")
