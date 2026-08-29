"""
Signaux pour les campagnes de dons.
Notification automatique selon la portée définie.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@receiver(post_save, sender='campaigns.Campaign')
def notify_campaign_created(sender, instance, created, **kwargs):
    """
    Quand une campagne est créée, notifie les personnes
    selon la portée définie (notification_scope).
    """
    if not created:
        return

    if instance.notification_scope == 'none' or instance.notification_sent:
        return

    recipients = instance.get_notification_recipients()
    if not recipients:
        return

    # Notification in-app aux admins
    try:
        from apps.communication.models import Notification
        from apps.accounts.models import User
        from django.db.models import Q

        admins = User.objects.filter(is_active=True).filter(
            Q(is_superuser=True) | Q(role__icontains='admin')
        ).distinct()

        for admin in admins:
            Notification.objects.create(
                user=admin,
                title=f"📢 Nouvelle campagne : {instance.name}",
                message=(
                    f"Objectif : {instance.goal_amount}€\n"
                    f"Du {instance.start_date.strftime('%d/%m/%Y')} "
                    f"au {instance.end_date.strftime('%d/%m/%Y')}\n"
                    f"Portée : {instance.get_notification_scope_display()}\n"
                    f"{len(recipients)} personne(s) notifiée(s)"
                ),
                notification_type='info',
            )
    except Exception as e:
        logger.warning("Campaign admin notification failed: %s", e)

    # Email aux destinataires
    subject = f"📢 Nouvelle campagne : {instance.name} — EEBC"
    for email in recipients:
        try:
            send_mail(
                subject=subject,
                message=(
                    f"Bonjour,\n\n"
                    f"Une nouvelle campagne a été lancée :\n\n"
                    f"  {instance.name}\n"
                    f"  Objectif : {instance.goal_amount}€\n"
                    f"  Du {instance.start_date.strftime('%d/%m/%Y')} "
                    f"au {instance.end_date.strftime('%d/%m/%Y')}\n\n"
                    f"{instance.description[:300] if instance.description else ''}\n\n"
                    f"Pour contribuer, rendez-vous sur https://eglise-ebc.org/don/\n\n"
                    f"Fraternellement,\n"
                    f"Église Évangélique Baptiste de Cabassou"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception as e:
            logger.warning("Campaign email to %s failed: %s", email, e)

    # Marquer comme notifié
    sender.objects.filter(pk=instance.pk).update(notification_sent=True)
    logger.info("Campaign '%s' notified %d recipients", instance.name, len(recipients))
