"""
Signals pour les modèles Member.
Gère la logique métier déclenchée par les événements du modèle.
"""
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Member, LifeEvent, VisitationLog


@receiver(pre_save, sender=Member)
def generate_member_id_on_create(sender, instance, **kwargs):
    """
    Génère automatiquement l'ID membre lors de la création.
    """
    if not instance.member_id:
        instance.member_id = Member.objects.generate_member_id(instance.site)


@receiver(post_save, sender=Member)
def log_member_creation(sender, instance, created, **kwargs):
    """
    Log la création d'un nouveau membre dans l'audit trail.
    """
    if created:
        from apps.core.models import AuditLog
        from apps.core.signals import get_current_request
        
        request = get_current_request()
        user = request.user if request and request.user.is_authenticated else None
        
        AuditLog.objects.create(
            user=user,
            action='member_created',
            model_name='Member',
            object_id=instance.pk,
            object_repr=str(instance),
            changes={
                'member_id': instance.member_id,
                'full_name': instance.full_name,
                'site': str(instance.site) if instance.site else None,
            },
            ip_address=request.META.get('REMOTE_ADDR') if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else '',
        )


@receiver(post_save, sender=LifeEvent)
def handle_life_event_created(sender, instance, created, **kwargs):
    """
    Gère les actions automatiques lors de la création d'un événement de vie.
    """
    if created:
        # Créer automatiquement une visite si requise
        if instance.requires_visit:
            from datetime import date, timedelta
            
            # Programmer la visite dans les 7 jours
            scheduled_date = date.today() + timedelta(days=7)
            
            VisitationLog.objects.create(
                member=instance.primary_member,
                life_event=instance,
                status='planifie',
                scheduled_date=scheduled_date,
                visit_type='domicile',
                summary=f"Visite suite à : {instance.title}"
            )
        
        # Notifier les responsables si événement prioritaire
        if instance.priority == 'haute':
            from .notifications import MemberNotificationService
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            # Notifier les pasteurs et responsables
            pastors = User.objects.filter(
                role__in=['admin', 'secretariat']
            ).exclude(email='')
            
            recipients = [(user.email, user.get_full_name()) for user in pastors]
            
            if recipients:
                MemberNotificationService.notify_life_event(
                    life_event=instance,
                    recipients=recipients
                )


@receiver(post_save, sender=VisitationLog)
def handle_visit_completed(sender, instance, **kwargs):
    """
    Gère les actions automatiques lors de la completion d'une visite.
    """
    if instance.status == 'effectue' and instance.life_event:
        # Marquer l'événement de vie comme visité
        instance.life_event.visit_completed = True
        instance.life_event.save(update_fields=['visit_completed'])


@receiver(post_delete, sender=Member)
def log_member_deletion(sender, instance, **kwargs):
    """
    Log la suppression d'un membre dans l'audit trail.
    """
    from apps.core.models import AuditLog
    from apps.core.signals import get_current_request
    
    request = get_current_request()
    user = request.user if request and request.user.is_authenticated else None
    
    AuditLog.objects.create(
        user=user,
        action='member_deleted',
        model_name='Member',
        object_id=instance.pk,
        object_repr=str(instance),
        changes={
            'member_id': instance.member_id,
            'full_name': instance.full_name,
            'deletion_reason': 'Manual deletion',
        },
        ip_address=request.META.get('REMOTE_ADDR') if request else None,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else '',
    )