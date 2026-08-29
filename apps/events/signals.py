"""
Signals pour synchroniser les événements internes avec les événements publics
et déclencher les notifications.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.text import slugify
from .models import Event


@receiver(post_save, sender=Event)
def sync_public_event(sender, instance, created, **kwargs):
    """
    Synchronise un Event avec PublicEvent quand visibility='public'.
    Crée ou met à jour le PublicEvent correspondant.
    """
    from apps.core.models import PublicEvent
    
    if instance.visibility == 'public':
        # Générer un slug unique
        base_slug = slugify(instance.title)
        slug = base_slug
        counter = 1
        
        # Vérifier si un PublicEvent existe déjà pour cet Event
        existing = PublicEvent.objects.filter(internal_event=instance).first()
        
        if existing:
            # Mettre à jour l'existant
            existing.title = instance.title
            existing.description = instance.description or instance.title
            existing.start_date = instance.start_date
            existing.start_time = instance.start_time
            existing.end_date = instance.end_date
            existing.end_time = instance.end_time
            existing.location = instance.location or ''
            existing.site = instance.site
            existing.is_published = True
            existing.save()
        else:
            # Créer un nouveau PublicEvent
            # S'assurer que le slug est unique
            while PublicEvent.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            PublicEvent.objects.create(
                internal_event=instance,
                title=instance.title,
                slug=slug,
                description=instance.description or instance.title,
                start_date=instance.start_date,
                start_time=instance.start_time,
                end_date=instance.end_date,
                end_time=instance.end_time,
                location=instance.location or '',
                site=instance.site,
                is_published=True,
                allow_registration=False,
            )
    else:
        # Si l'événement n'est plus public, dépublier le PublicEvent
        from apps.core.models import PublicEvent
        PublicEvent.objects.filter(internal_event=instance).update(is_published=False)


@receiver(post_delete, sender=Event)
def delete_public_event(sender, instance, **kwargs):
    """
    Supprime le PublicEvent quand l'Event interne est supprimé.
    """
    from apps.core.models import PublicEvent
    PublicEvent.objects.filter(internal_event=instance).delete()


@receiver(post_save, sender=Event)
def notify_new_event(sender, instance, created, **kwargs):
    """
    Quand un événement est créé avec notification_scope != 'none',
    notifie immédiatement les responsables (notification in-app).
    Les rappels par email sont gérés par la commande run_notifications.
    """
    if not created:
        return

    if instance.notification_scope == 'none' or instance.is_cancelled:
        return

    from apps.communication.models import Notification
    from apps.accounts.models import User

    # Notifier les admins qu'un nouvel événement a été créé
    admins = User.objects.filter(is_active=True, is_superuser=True)
    date_str = instance.start_date.strftime('%d/%m/%Y')
    time_str = instance.start_time.strftime('%H:%M') if instance.start_time else ''

    for admin in admins:
        Notification.objects.create(
            user=admin,
            title=f"📌 Nouvel événement : {instance.title}",
            message=(
                f"Un nouvel événement a été créé : {instance.title}\n"
                f"Date : {date_str}{' à ' + time_str if time_str else ''}\n"
                f"{'Lieu : ' + instance.location if instance.location else ''}\n"
                f"Portée notifications : {instance.get_notification_scope_display()}"
            ),
            notification_type='info',
        )


@receiver(post_save, sender=Event)
def notify_event_cancelled(sender, instance, created, **kwargs):
    """
    Quand un événement est annulé, notifie les destinataires concernés.
    """
    if created or not instance.is_cancelled:
        return

    from apps.communication.models import Notification
    from apps.accounts.models import User

    recipients = instance.get_notification_recipients()
    if not recipients:
        return

    # Notification in-app aux admins
    admins = User.objects.filter(is_active=True, is_superuser=True)
    for admin in admins:
        Notification.objects.create(
            user=admin,
            title=f"❌ Événement annulé : {instance.title}",
            message=f"L'événement {instance.title} du {instance.start_date.strftime('%d/%m/%Y')} a été annulé.",
            notification_type='warning',
        )

    # Email aux destinataires
    from django.core.mail import send_mail
    from django.conf import settings as django_settings

    for email in recipients:
        try:
            send_mail(
                subject=f"❌ Événement annulé : {instance.title}",
                message=(
                    f"L'événement « {instance.title} » prévu le "
                    f"{instance.start_date.strftime('%d/%m/%Y')} a été annulé.\n\n"
                    f"Nous nous excusons pour la gêne occasionnée.\n\n"
                    f"-- EEBC"
                ),
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception:
            pass
