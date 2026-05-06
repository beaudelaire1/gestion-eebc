"""
Signaux pour le module Transport.
Déclenche les notifications lors des changements de statut.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TransportRequest
from .notifications import (
    send_driver_accepted_notification,
    send_driver_en_route_notification,
    send_driver_arriving_notification,
    send_driver_completed_notification,
)
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=TransportRequest)
def notify_on_status_change(sender, instance, created, **kwargs):
    """
    Déclenche les notifications quand le statut d'une demande change.
    
    Transitions:
    - PENDING → CONFIRMED: Chauffeur accepté
    - CONFIRMED → EN_ROUTE: Chauffeur en route
    - EN_ROUTE → ARRIVING: Chauffeur arrive bientôt
    - ARRIVING/EN_ROUTE → COMPLETED: Trajet effectué
    """
    if created:
        # Nouvelle demande, pas de notification
        return
    
    # Récupérer le statut précédent (pas directement disponible dans le signal)
    # On va devoir vérifier en comparant avec la DB
    try:
        previous = TransportRequest.objects.get(pk=instance.pk)
    except TransportRequest.DoesNotExist:
        return
    
    # Vérifier si le statut a changé
    previous_status = previous.status
    current_status = instance.status
    
    if previous_status == current_status:
        # Pas de changement de statut
        return
    
    # Notifier selon la transition
    if current_status == TransportRequest.Status.CONFIRMED and previous_status == TransportRequest.Status.PENDING:
        # Chauffeur a accepté
        try:
            send_driver_accepted_notification(instance)
        except Exception as e:
            logger.error(f"Error sending accepted notification: {e}")
    
    elif current_status == TransportRequest.Status.EN_ROUTE and previous_status == TransportRequest.Status.CONFIRMED:
        # Chauffeur a démarré
        try:
            send_driver_en_route_notification(instance)
        except Exception as e:
            logger.error(f"Error sending en_route notification: {e}")
    
    elif current_status == TransportRequest.Status.ARRIVING and previous_status == TransportRequest.Status.EN_ROUTE:
        # Chauffeur arrive bientôt
        try:
            send_driver_arriving_notification(instance)
        except Exception as e:
            logger.error(f"Error sending arriving notification: {e}")
    
    elif current_status == TransportRequest.Status.COMPLETED and previous_status in [
        TransportRequest.Status.ARRIVING, 
        TransportRequest.Status.EN_ROUTE
    ]:
        # Trajet effectué
        try:
            send_driver_completed_notification(instance)
        except Exception as e:
            logger.error(f"Error sending completed notification: {e}")
