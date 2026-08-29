"""
Commande de gestion pour exécuter les notifications sans Celery.
Peut être lancée via cron Render ou manuellement.

Usage:
    python manage.py run_notifications              # Tout exécuter
    python manage.py run_notifications --events     # Rappels événements seulement
    python manage.py run_notifications --birthdays  # Anniversaires seulement
    python manage.py run_notifications --absences   # Alertes absences seulement
"""
from datetime import date, timedelta
import logging

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Exécute les notifications planifiées (rappels événements, anniversaires, absences)'

    def add_arguments(self, parser):
        parser.add_argument('--events', action='store_true', help='Rappels événements')
        parser.add_argument('--birthdays', action='store_true', help='Vœux anniversaires')
        parser.add_argument('--absences', action='store_true', help='Alertes absences membres')
        parser.add_argument('--all', action='store_true', help='Tout exécuter (défaut)')

    def handle(self, *args, **options):
        run_all = options['all'] or not (options['events'] or options['birthdays'] or options['absences'])

        if run_all or options['events']:
            self._send_event_reminders()

        if run_all or options['birthdays']:
            self._send_birthday_wishes()

        if run_all or options['absences']:
            self._check_member_absences()

        self.stdout.write(self.style.SUCCESS('Notifications terminées.'))

    def _send_event_reminders(self):
        """Envoie les rappels d'événements selon notify_before."""
        from apps.events.models import Event

        today = date.today()
        events = Event.objects.filter(
            is_cancelled=False,
            notification_sent=False,
            start_date__gte=today,
        ).exclude(notification_scope='none')

        sent = 0
        for event in events:
            notify_date = event.start_date - timedelta(days=event.notify_before)
            if notify_date <= today:
                recipients = event.get_notification_recipients()
                if recipients:
                    days_until = (event.start_date - today).days
                    time_str = event.start_time.strftime('%H:%M') if event.start_time else ''
                    location = event.location or ''

                    subject = f"📅 Rappel : {event.title} dans {days_until} jour(s)"
                    message = (
                        f"Rappel : {event.title}\n\n"
                        f"Date : {event.start_date.strftime('%d/%m/%Y')}\n"
                        f"{'Heure : ' + time_str if time_str else ''}\n"
                        f"{'Lieu : ' + location if location else ''}\n\n"
                        f"{event.description[:300] if event.description else ''}\n\n"
                        f"-- EEBC"
                    )

                    for email in recipients:
                        try:
                            send_mail(
                                subject=subject,
                                message=message,
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                recipient_list=[email],
                                fail_silently=True,
                            )
                        except Exception as e:
                            logger.warning("Event reminder failed for %s: %s", email, e)

                    event.notification_sent = True
                    event.save(update_fields=['notification_sent'])
                    sent += 1
                    self.stdout.write(f'  ✓ Rappel envoyé : {event.title} ({len(recipients)} destinataires)')

        self.stdout.write(f'  → {sent} rappel(s) d\'événement envoyé(s)')

    def _send_birthday_wishes(self):
        """Envoie les vœux d'anniversaire."""
        from apps.members.models import Member

        today = date.today()
        members = Member.objects.filter(
            status='actif',
            date_of_birth__month=today.month,
            date_of_birth__day=today.day,
        )

        sent = 0
        for member in members:
            if member.email:
                try:
                    send_mail(
                        subject=f"🎂 Joyeux anniversaire {member.first_name} !",
                        message=(
                            f"Cher(e) {member.first_name},\n\n"
                            f"Toute l'église EEBC vous souhaite un merveilleux anniversaire !\n"
                            f"Que le Seigneur vous bénisse abondamment.\n\n"
                            f"« L'Éternel te bénisse et te garde ! » — Nombres 6:24\n\n"
                            f"Avec toute notre affection,\n"
                            f"L'équipe EEBC"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[member.email],
                        fail_silently=True,
                    )
                    sent += 1
                    self.stdout.write(f'  ✓ Anniversaire : {member.full_name}')
                except Exception as e:
                    logger.warning("Birthday wish failed for %s: %s", member.email, e)

        self.stdout.write(f'  → {sent} vœu(x) d\'anniversaire envoyé(s)')

    def _check_member_absences(self):
        """Alerte les responsables pour les membres non visités depuis longtemps."""
        from apps.communication.models import Notification
        from apps.accounts.models import User

        from apps.members.models import Member

        threshold_days = 180
        threshold_date = date.today() - timedelta(days=threshold_days)

        needing_visit = []
        for member in Member.objects.filter(status='actif'):
            last = member.last_visit_date if hasattr(member, 'last_visit_date') else None
            if last is None or last < threshold_date:
                needing_visit.append(member)

        if not needing_visit:
            self.stdout.write('  → Aucun membre nécessitant une visite.')
            return

        admins = User.objects.filter(is_active=True, is_superuser=True)
        msg_lines = [f"{len(needing_visit)} membre(s) non visité(s) depuis 6+ mois :"]
        for m in needing_visit[:15]:
            msg_lines.append(f"• {m.full_name}")
        if len(needing_visit) > 15:
            msg_lines.append(f"... et {len(needing_visit) - 15} autres.")

        message = "\n".join(msg_lines)

        for admin in admins:
            Notification.objects.create(
                user=admin,
                title="📋 Rappel : Visites pastorales nécessaires",
                message=message,
                notification_type='info',
            )

        self.stdout.write(f'  → {len(needing_visit)} membre(s) signalé(s) aux responsables')
