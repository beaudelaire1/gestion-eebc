"""Signaux pour le module Worship."""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import WorshipService, ServiceRole


@receiver(post_save, sender=ServiceRole)
def notify_role_assignment(sender, instance, created, **kwargs):
    """
    Notifie le membre quand il est assigné à un rôle.
    """
    if not created:
        return
    
    # Ne notifier que si un membre est assigné
    if not instance.member and not instance.user:
        return
    
    from apps.communication.models import Notification
    
    # Déterminer le destinataire
    recipient = None
    if instance.member and instance.member.user:
        recipient = instance.member.user
    elif instance.user:
        recipient = instance.user
    
    if not recipient:
        return
    
    service_date = instance.service.event.start_date.strftime('%d/%m/%Y')
    
    Notification.objects.create(
        recipient=recipient,
        title=f"Assignation : {instance.get_role_display()}",
        message=f"Vous avez été assigné(e) au rôle de {instance.get_role_display()} "
                f"pour le service du {service_date}. Merci de confirmer votre disponibilité.",
        notification_type='event',
        link=f"/app/worship/services/{instance.service.pk}/"
    )
    
    # Marquer comme notifié
    from django.utils import timezone
    instance.notified_at = timezone.now()
    instance.save(update_fields=['notified_at'])


@receiver(post_save, sender=WorshipService)
def create_default_roles(sender, instance, created, **kwargs):
    """
    Crée les rôles par défaut pour un nouveau service.
    """
    if not created:
        return
    
    default_roles = [
        ServiceRole.RoleType.PREDICATEUR,
        ServiceRole.RoleType.DIRIGEANT,
        ServiceRole.RoleType.SONORISATION,
        ServiceRole.RoleType.ACCUEIL,
        ServiceRole.RoleType.OFFRANDES,
    ]
    
    for role in default_roles:
        ServiceRole.objects.get_or_create(
            service=instance,
            role=role,
            defaults={'status': ServiceRole.Status.EN_ATTENTE}
        )
