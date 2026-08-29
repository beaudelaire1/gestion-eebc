"""
Notifications pour le module Transport.
Gère l'envoi d'emails/SMS aux demandeurs et chauffeurs.
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from apps.communication.notification_service import NotificationService

logger = logging.getLogger(__name__)


def send_driver_accepted_notification(transport_request):
    """
    Notifie le demandeur que sa demande a été acceptée par un chauffeur.
    
    Contenu:
    - Nom du chauffeur
    - Contact du chauffeur
    - Véhicule (type, capacité)
    - Date/heure du trajet
    """
    if not transport_request.requester_email:
        logger.warning(f"No email for requester of request {transport_request.pk}")
        return
    
    subject = f'Transport confirmé pour le {transport_request.event_date.strftime("%d/%m/%Y")}'
    
    context = {
        'transport_request': transport_request,
        'driver': transport_request.driver,
        'requester_name': transport_request.requester_name,
    }
    
    html_message = render_to_string('emails/transport_driver_accepted.html', context)
    
    try:
        send_mail(
            subject=subject,
            message=f"Transport confirmé pour {transport_request.requester_name}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[transport_request.requester_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent acceptance notification for request {transport_request.pk}")
    except Exception as e:
        logger.error(f"Failed to send acceptance notification: {e}")


def send_driver_en_route_notification(transport_request):
    """
    Notifie le demandeur que le chauffeur est en route.
    
    Contenu:
    - Confirmation chauffeur en route
    - ETA approximatif
    - Numéro de téléphone chauffeur
    """
    if not transport_request.requester_email:
        logger.warning(f"No email for requester of request {transport_request.pk}")
        return
    
    subject = f'Chauffeur en route pour le {transport_request.event_date.strftime("%d/%m/%Y")}'
    
    context = {
        'transport_request': transport_request,
        'driver': transport_request.driver,
        'requester_name': transport_request.requester_name,
    }
    
    html_message = render_to_string('emails/transport_driver_en_route.html', context)
    
    try:
        send_mail(
            subject=subject,
            message=f"Chauffeur en route - {transport_request.requester_name}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[transport_request.requester_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent en_route notification for request {transport_request.pk}")
    except Exception as e:
        logger.error(f"Failed to send en_route notification: {e}")


def send_driver_arriving_notification(transport_request):
    """
    Notifie le demandeur que le chauffeur arrive bientôt (dans 2-5 min).
    
    Contenu:
    - Alerte: chauffeur arrive bientôt
    - Numéro de téléphone chauffeur
    - Lieu de prise en charge
    """
    if not transport_request.requester_email:
        logger.warning(f"No email for requester of request {transport_request.pk}")
        return
    
    subject = f'Le chauffeur arrive bientôt - {transport_request.event_date.strftime("%d/%m/%Y")}'
    
    context = {
        'transport_request': transport_request,
        'driver': transport_request.driver,
        'requester_name': transport_request.requester_name,
    }
    
    html_message = render_to_string('emails/transport_driver_arriving.html', context)
    
    try:
        send_mail(
            subject=subject,
            message=f"Chauffeur arrive bientôt - {transport_request.requester_name}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[transport_request.requester_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent arriving notification for request {transport_request.pk}")
    except Exception as e:
        logger.error(f"Failed to send arriving notification: {e}")


def send_driver_completed_notification(transport_request):
    """
    Notifie le demandeur que le trajet est complété et remercie le chauffeur.
    
    Contenu:
    - Confirmation trajet effectué
    - Merci
    """
    if not transport_request.requester_email:
        logger.warning(f"No email for requester of request {transport_request.pk}")
        return
    
    subject = f'Transport effectué - {transport_request.event_date.strftime("%d/%m/%Y")}'
    
    context = {
        'transport_request': transport_request,
        'driver': transport_request.driver,
        'requester_name': transport_request.requester_name,
    }
    
    html_message = render_to_string('emails/transport_driver_completed.html', context)
    
    try:
        send_mail(
            subject=subject,
            message=f"Transport effectué - {transport_request.requester_name}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[transport_request.requester_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent completed notification for request {transport_request.pk}")
    except Exception as e:
        logger.error(f"Failed to send completed notification: {e}")
