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
    from .services import send_whatsapp_parent_event_reminder
    
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
                whatsapp_result = send_whatsapp_parent_event_reminder(event)
                event.notification_sent = True
                event.save(update_fields=['notification_sent'])
                sent_count += 1
                logger.info(f"Reminder sent for event: {event.title}")
                if not whatsapp_result.get('skipped'):
                    logger.info(
                        "WhatsApp parents reminder for %s: %s sent / %s failed",
                        event.title,
                        whatsapp_result.get('sent', 0),
                        whatsapp_result.get('failed', 0),
                    )
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
    de l'année précédente. Inclut les 3 sources de dons :
    - FinancialTransaction (dons/dîmes/offrandes)
    - OnlineDonation (Stripe)
    - CampaignDonation (campagnes)
    """
    from apps.finance.models import FinancialTransaction, OnlineDonation, TaxReceipt
    from apps.members.models import Member
    from apps.campaigns.models import Donation as CampaignDonation
    from django.db.models import Sum, Q
    
    if year is None:
        year = date.today().year - 1
    
    # Trouver tous les membres potentiellement donateurs via les 3 sources
    members_with_transactions = set(
        FinancialTransaction.objects.filter(
            member__isnull=False,
            transaction_date__year=year,
            status='valide',
            transaction_type__in=['don', 'dime', 'offrande'],
        ).values_list('member_id', flat=True)
    )
    
    members_with_online = set(
        OnlineDonation.objects.filter(
            member__isnull=False,
            status='completed',
            created_at__year=year,
        ).values_list('member_id', flat=True)
    )
    
    all_member_ids = members_with_transactions | members_with_online
    
    # Ajouter les membres identifiés par nom via les dons de campagne
    members = Member.objects.filter(
        Q(pk__in=all_member_ids) | Q(status='actif')
    ).distinct()
    
    created_count = 0
    skipped_count = 0
    
    for member in members:
        # Vérifier qu'il n'y a pas déjà un reçu pour ce membre cette année
        if TaxReceipt.objects.filter(member=member, fiscal_year=year).exists():
            skipped_count += 1
            continue
        
        # 1. Transactions financières
        transactions = FinancialTransaction.objects.filter(
            member=member,
            transaction_date__year=year,
            status='valide',
            transaction_type__in=['don', 'dime', 'offrande'],
        )
        total_transactions = transactions.aggregate(total=Sum('amount'))['total'] or 0
        
        # 2. Dons en ligne
        online = OnlineDonation.objects.filter(
            member=member,
            status='completed',
            created_at__year=year,
        )
        total_online = online.aggregate(total=Sum('amount'))['total'] or 0
        
        # 3. Dons de campagne (par nom)
        campaign_total = CampaignDonation.objects.filter(
            donor_name=member.full_name,
            is_cancelled=False,
            donation_date__year=year,
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total = total_transactions + total_online + campaign_total
        
        if total <= 0:
            continue
        
        # Générer le numéro de reçu
        last_receipt = TaxReceipt.objects.filter(fiscal_year=year).order_by('-receipt_number').first()
        if last_receipt:
            try:
                last_num = int(last_receipt.receipt_number.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        receipt_number = f"RF-{year}-{new_num:04d}"
        
        # Créer le reçu fiscal
        receipt = TaxReceipt.objects.create(
            receipt_number=receipt_number,
            fiscal_year=year,
            donor_name=member.full_name,
            donor_address=f"{member.address or ''}, {member.postal_code or ''} {member.city or ''}".strip(', '),
            donor_email=member.email or '',
            member=member,
            total_amount=total,
            status='draft',
        )
        
        # Associer les transactions financières
        if transactions.exists():
            receipt.transactions.set(transactions)
        
        created_count += 1
        logger.info(f"Tax receipt {receipt_number} created for {member.full_name}: {total}€")
    
    return f"Created {created_count} tax receipts for year {year} (skipped {skipped_count} existing)"


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
