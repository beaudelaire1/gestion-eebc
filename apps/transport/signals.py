"""Signaux pour le module Transport."""
import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from . import notifications
from .models import TransportRequest

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=TransportRequest)
def store_previous_status(sender, instance, **kwargs):
    """Mémorise l'ancien statut avant sauvegarde pour le signal post_save."""
    if not instance.pk:
        instance._previous_status = None
        return

    instance._previous_status = sender.objects.filter(pk=instance.pk).values_list(
        'status', flat=True
    ).first()


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
        return

    previous_status = getattr(instance, '_previous_status', None)
    current_status = instance.status

    if previous_status == current_status:
        return

    try:
        if (
            previous_status == TransportRequest.Status.PENDING
            and current_status == TransportRequest.Status.CONFIRMED
        ):
            notifications.send_driver_accepted_notification(instance)
        elif (
            previous_status == TransportRequest.Status.CONFIRMED
            and current_status == TransportRequest.Status.EN_ROUTE
        ):
            notifications.send_driver_en_route_notification(instance)
        elif (
            previous_status == TransportRequest.Status.EN_ROUTE
            and current_status == TransportRequest.Status.ARRIVING
        ):
            notifications.send_driver_arriving_notification(instance)
        elif (
            previous_status in [TransportRequest.Status.ARRIVING, TransportRequest.Status.EN_ROUTE]
            and current_status == TransportRequest.Status.COMPLETED
        ):
            notifications.send_driver_completed_notification(instance)
    except Exception:
        logger.exception(
            "Error sending transport notification for request %s (%s -> %s)",
            instance.pk,
            previous_status,
            current_status,
        )
