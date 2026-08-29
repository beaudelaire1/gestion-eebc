"""
Signaux pour le Club Biblique.
Gère les notifications automatiques lors de la prise de présence.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='bibleclub.Attendance')
def notify_absence(sender, instance, created, **kwargs):
    """
    Quand un enfant est marqué absent, notifie les parents par email
    et le responsable de la classe (moniteur principal).
    """
    if instance.status not in ('absent', 'absent_notified'):
        return

    # Éviter de re-notifier
    if instance.status == 'absent_notified':
        return

    child = instance.child
    session = instance.session

    # 1. Notifier les parents
    _notify_parents(child, session)

    # 2. Notifier le moniteur principal de la classe
    _notify_lead_monitor(child, session)

    # 3. Marquer comme notifié
    sender.objects.filter(pk=instance.pk).update(status='absent_notified')


def _notify_parents(child, session):
    """Envoie un email aux parents de l'enfant absent."""
    from django.core.mail import send_mail
    from django.conf import settings

    parents = []
    if child.father_email:
        parents.append((child.father_email, child.father_name))
    if child.mother_email:
        parents.append((child.mother_email, child.mother_name))

    if not parents:
        return

    date_str = session.date.strftime('%d/%m/%Y')
    class_name = str(child.bible_class) if child.bible_class else 'Club Biblique'

    for email, name in parents:
        try:
            send_mail(
                subject=f"Absence de {child.first_name} - Club Biblique EEBC",
                message=(
                    f"Bonjour {name or 'Cher parent'},\n\n"
                    f"Nous vous informons que {child.first_name} {child.last_name} "
                    f"était absent(e) à la session du {date_str} ({class_name}).\n\n"
                    f"Si cette absence est prévue, merci de nous en informer.\n"
                    f"Si vous avez des questions, n'hésitez pas à nous contacter.\n\n"
                    f"Fraternellement,\n"
                    f"L'équipe du Club Biblique EEBC"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception as e:
            logger.warning("Absence notification to %s failed: %s", email, e)


def _notify_lead_monitor(child, session):
    """Notifie le moniteur principal de la classe."""
    from apps.communication.models import Notification

    bible_class = child.bible_class
    if not bible_class:
        return

    lead_monitors = bible_class.monitors.filter(is_lead=True, is_active=True)
    date_str = session.date.strftime('%d/%m/%Y')

    for monitor in lead_monitors:
        if monitor.user:
            Notification.objects.create(
                user=monitor.user,
                title=f"Absence : {child.first_name} {child.last_name}",
                message=(
                    f"{child.first_name} {child.last_name} était absent(e) "
                    f"à la session du {date_str}."
                ),
                notification_type='warning',
            )
