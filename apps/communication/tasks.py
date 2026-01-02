"""
Tâches Celery pour les notifications automatiques.

Ces tâches sont exécutées de manière asynchrone pour :
- Rappels d'événements
- Notifications d'anniversaires
- Alertes d'absence
- Envoi de reçus fiscaux
"""

from celery import shared_task
from django.utils import timezone
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_event_reminders():
    """
    Envoie les rappels d'événements.
    
    Exécuté quotidiennement pour envoyer les rappels
    selon le paramètre notify_before de chaque événement.
    """
    from apps.events.models import Event
    from .notification_service import notification_service
    
    today = date.today()
    
    # Trouver les événements à notifier
    events = Event.objects.filter(
        is_cancelled=False,
        notification_sent=False,
        start_date__gte=today,
    ).exclude(
        notification_scope='none'
    )
    
    sent_count = 0
    
    for event in events:
        # Vérifier si c'est le bon jour pour notifier
        notify_date = event.start_date - timedelta(days=event.notify_before)
        
        if notify_date <= today:
            try:
                notification_service.send_event_reminder(event)
                event.notification_sent = True
                event.save(update_fields=['notification_sent'])
                sent_count += 1
                logger.info(f"Reminder sent for event: {event.title}")
            except Exception as e:
                logger.error(f"Failed to send reminder for event {event.id}: {e}")
    
    return f"Sent {sent_count} event reminders"


@shared_task
def send_birthday_notifications():
    """
    Envoie les vœux d'anniversaire.
    
    Exécuté quotidiennement pour envoyer des vœux
    aux membres dont c'est l'anniversaire.
    """
    from apps.members.models import Member
    from .notification_service import notification_service
    
    today = date.today()
    
    # Trouver les membres dont c'est l'anniversaire
    members = Member.objects.filter(
        status='actif',
        date_of_birth__month=today.month,
        date_of_birth__day=today.day,
    )
    
    sent_count = 0
    
    for member in members:
        if member.email or member.phone:
            try:
                notification_service.send_birthday_wishes(member)
                sent_count += 1
                logger.info(f"Birthday wishes sent to: {member.full_name}")
            except Exception as e:
                logger.error(f"Failed to send birthday wishes to {member.id}: {e}")
    
    return f"Sent {sent_count} birthday wishes"


@shared_task
def check_member_absences():
    """
    Vérifie les absences prolongées des membres.
    
    Exécuté hebdomadairement pour détecter les membres
    qui n'ont pas été vus depuis longtemps.
    """
    from apps.members.models import Member
    from .notification_service import notification_service
    
    # Membres actifs qui n'ont pas été visités depuis 3 mois
    threshold_days = 90
    
    members_needing_attention = []
    
    for member in Member.objects.filter(status='actif'):
        days = member.days_since_last_visit
        if days is None or days > threshold_days:
            weeks = (days or 999) // 7
            members_needing_attention.append((member, weeks))
    
    # Envoyer une alerte groupée aux responsables
    if members_needing_attention:
        for member, weeks in members_needing_attention:
            try:
                notification_service.send_absence_alert(member, weeks)
            except Exception as e:
                logger.error(f"Failed to send absence alert for {member.id}: {e}")
    
    return f"Checked {len(members_needing_attention)} members needing attention"


@shared_task
def generate_annual_tax_receipts(year=None):
    """
    Génère les reçus fiscaux annuels.
    
    Exécuté en janvier pour générer les reçus
    de l'année précédente.
    """
    from apps.finance.models import FinancialTransaction, TaxReceipt
    from apps.members.models import Member
    from django.db.models import Sum
    
    if year is None:
        year = date.today().year - 1
    
    # Trouver tous les membres avec des dons validés cette année
    members_with_donations = Member.objects.filter(
        transactions__transaction_date__year=year,
        transactions__status='valide',
        transactions__transaction_type__in=['don', 'dime', 'offrande'],
    ).distinct()
    
    created_count = 0
    
    for member in members_with_donations:
        # Calculer le total des dons
        transactions = FinancialTransaction.objects.filter(
            member=member,
            transaction_date__year=year,
            status='valide',
            transaction_type__in=['don', 'dime', 'offrande'],
        )
        
        total = transactions.aggregate(total=Sum('amount'))['total']
        
        if total and total > 0:
            # Créer le reçu fiscal
            receipt = TaxReceipt.objects.create(
                fiscal_year=year,
                donor_name=member.full_name,
                donor_address=f"{member.address}\n{member.postal_code} {member.city}",
                donor_email=member.email,
                member=member,
                total_amount=total,
                status='draft',
            )
            
            # Associer les transactions
            receipt.transactions.set(transactions)
            
            created_count += 1
            logger.info(f"Tax receipt created for {member.full_name}: {total}€")
    
    return f"Created {created_count} tax receipts for year {year}"


@shared_task
def send_donation_receipts_batch():
    """
    Envoie les reçus fiscaux en attente par email.
    """
    from apps.finance.models import TaxReceipt
    
    receipts = TaxReceipt.objects.filter(
        status='issued',
        donor_email__isnull=False,
    ).exclude(donor_email='')
    
    sent_count = 0
    
    for receipt in receipts:
        try:
            if not receipt.pdf_file:
                receipt.generate_pdf()
            receipt.send_by_email()
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send receipt {receipt.receipt_number}: {e}")
    
    return f"Sent {sent_count} tax receipts"


@shared_task
def cleanup_old_logs():
    """
    Nettoie les anciens logs de communication.
    
    Supprime les logs de plus de 6 mois.
    """
    from .models import EmailLog, SMSLog
    
    threshold = timezone.now() - timedelta(days=180)
    
    email_deleted = EmailLog.objects.filter(created_at__lt=threshold).delete()[0]
    sms_deleted = SMSLog.objects.filter(created_at__lt=threshold).delete()[0]
    
    return f"Deleted {email_deleted} email logs and {sms_deleted} SMS logs"
