"""Centre de notifications - signaux automatiques EEBC."""

import logging
from datetime import date, timedelta

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='communication.Announcement')
def handle_announcement_multichannel(sender, instance, created, **kwargs):
    """Deliver a requested announcement through email and WhatsApp.

    The legacy model still exposes ``notify_by_email`` and ``notify_by_sms``.
    Until a schema migration renames the latter, either notification checkbox
    means "deliver the announcement" and the delivery engine uses both channels,
    respecting each member's own email/WhatsApp opt-in.

    ``notify_by_sms`` is cleared only on the in-memory instance so the legacy
    view does not immediately send a duplicate WhatsApp message after save. The
    persisted value is deliberately left untouched for backward compatibility.
    """
    if not created or not (instance.notify_by_email or instance.notify_by_sms):
        return

    # Prevent the legacy announcement_create view from performing a second,
    # synchronous WhatsApp send after form.save(). This does not write to DB.
    instance.notify_by_sms = False
    announcement_id = instance.pk

    def dispatch():
        from celery import group

        from .channel_tasks import (
            send_announcement_email_task,
            send_announcement_whatsapp_task,
        )
        from .multichannel import (
            send_announcement_email,
            send_announcement_whatsapp,
        )

        try:
            group(
                send_announcement_email_task.s(announcement_id),
                send_announcement_whatsapp_task.s(announcement_id),
            ).apply_async()
            logger.info(
                "Announcement %s queued for email + WhatsApp delivery",
                announcement_id,
            )
        except Exception:
            # A broker outage must not silently lose an announcement. The HTTP
            # request may take longer, but both channels are attempted.
            logger.exception(
                "Celery unavailable for announcement %s; using synchronous fallback",
                announcement_id,
            )
            announcement = sender.objects.get(pk=announcement_id)
            email_result = send_announcement_email(announcement)
            whatsapp_result = send_announcement_whatsapp(announcement)
            logger.info(
                "Announcement %s synchronous delivery email=%s whatsapp=%s",
                announcement_id,
                email_result,
                whatsapp_result,
            )

    transaction.on_commit(dispatch)


@receiver(post_save, sender='members.LifeEvent')
def handle_life_event_notification(sender, instance, created, **kwargs):
    """Gère les notifications liées aux événements de vie."""
    if not created:
        return

    from apps.accounts.models import User
    from apps.communication.models import Notification
    from apps.members.models import VisitationLog

    pastors = (
        User.objects.filter(role__icontains='pasteur', is_active=True)
        | User.objects.filter(role__icontains='admin', is_active=True)
    )

    if instance.event_type == 'naissance':
        for pastor in pastors:
            Notification.objects.create(
                user=pastor,
                title=f"🎉 Naissance à annoncer : {instance.title}",
                message=(
                    f"Une naissance a été enregistrée pour {instance.primary_member.full_name}. "
                    "Pensez à l'annoncer lors du prochain culte."
                ),
                notification_type='info',
                action_url=f"/admin/members/lifeevent/{instance.pk}/change/",
            )

    elif instance.event_type == 'deces':
        for pastor in pastors:
            Notification.objects.create(
                user=pastor,
                title=f"⚫ Décès : {instance.title}",
                message=(
                    f"Un décès a été enregistré concernant {instance.primary_member.full_name}. "
                    "Une visite pastorale est recommandée."
                ),
                notification_type='warning',
                action_url=f"/admin/members/lifeevent/{instance.pk}/change/",
            )

        if instance.requires_visit:
            main_pastor = User.objects.filter(is_superuser=True, is_active=True).first()
            VisitationLog.objects.create(
                visitor=main_pastor,
                member=instance.primary_member,
                visit_type='domicile',
                status='a_faire',
                life_event=instance,
                summary=f"Visite suite au décès : {instance.title}",
            )

    elif instance.event_type == 'hospitalisation':
        for pastor in pastors:
            Notification.objects.create(
                user=pastor,
                title=f"🏥 Hospitalisation : {instance.primary_member.full_name}",
                message=(
                    f"{instance.primary_member.full_name} est hospitalisé(e). "
                    "Une visite est recommandée."
                ),
                notification_type='warning',
                action_url=f"/admin/members/lifeevent/{instance.pk}/change/",
            )

        if instance.requires_visit:
            main_pastor = User.objects.filter(is_superuser=True, is_active=True).first()
            VisitationLog.objects.create(
                visitor=main_pastor,
                member=instance.primary_member,
                visit_type='hopital',
                status='a_faire',
                life_event=instance,
                summary=f"Visite hospitalière : {instance.description or instance.title}",
            )

    elif instance.event_type == 'mariage':
        for pastor in pastors:
            Notification.objects.create(
                user=pastor,
                title=f"💒 Mariage à annoncer : {instance.title}",
                message=(
                    "Un mariage a été enregistré. Pensez à féliciter le couple "
                    "et à l'annoncer lors du prochain culte."
                ),
                notification_type='success',
                action_url=f"/admin/members/lifeevent/{instance.pk}/change/",
            )

    elif instance.event_type == 'bapteme':
        for pastor in pastors:
            Notification.objects.create(
                user=pastor,
                title=f"💧 Baptême : {instance.primary_member.full_name}",
                message=(
                    f"Un baptême a été enregistré pour {instance.primary_member.full_name}."
                ),
                notification_type='success',
                action_url=f"/admin/members/lifeevent/{instance.pk}/change/",
            )


@receiver(post_save, sender='members.VisitationLog')
def handle_visit_completion(sender, instance, created, **kwargs):
    """Notifie quand une visite est marquée comme effectuée."""
    if created:
        return

    if instance.status == 'effectue' and instance.life_event:
        instance.life_event.visit_completed = True
        instance.life_event.save(update_fields=['visit_completed'])


def get_members_needing_visit():
    """Retourne les membres non visités depuis six mois."""
    from apps.members.models import Member

    six_months_ago = date.today() - timedelta(days=180)
    members_needing_visit = []

    for member in Member.objects.filter(status='actif'):
        last_visit = member.last_visit_date
        if last_visit is None or last_visit < six_months_ago:
            members_needing_visit.append(
                {
                    'member': member,
                    'last_visit': last_visit,
                    'days_since': member.days_since_last_visit,
                }
            )

    return members_needing_visit


def send_weekly_visit_reminder():
    """Envoie un rappel hebdomadaire aux pasteurs."""
    from apps.accounts.models import User
    from apps.communication.models import Notification

    members = get_members_needing_visit()
    if not members:
        return

    message_lines = [
        f"📋 {len(members)} membre(s) n'ont pas été visités depuis plus de 6 mois :\n"
    ]
    for item in members[:10]:
        member = item['member']
        days = item['days_since']
        if days:
            message_lines.append(f"• {member.full_name} ({days} jours)")
        else:
            message_lines.append(f"• {member.full_name} (jamais visité)")

    if len(members) > 10:
        message_lines.append(f"\n... et {len(members) - 10} autres.")

    message = "\n".join(message_lines)
    pastors = (
        User.objects.filter(role__icontains='pasteur', is_active=True)
        | User.objects.filter(role__icontains='admin', is_active=True)
    )

    for pastor in pastors:
        Notification.objects.create(
            user=pastor,
            title="📅 Rappel hebdomadaire : Visites pastorales",
            message=message,
            notification_type='info',
            action_url="/admin/members/visitationlog/?status=a_faire",
        )
