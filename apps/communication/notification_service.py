"""
Service de Notifications Multicanales pour EEBC.

Gère l'envoi de notifications via :
- Email (Django mail)
- SMS (Twilio)
- WhatsApp (Twilio)
- Push (préparé pour futur)

Utilisation :
    from apps.communication.notification_service import NotificationService
    
    service = NotificationService()
    service.send_notification(
        recipient=member,
        message="Votre message",
        channels=['email', 'sms', 'whatsapp']
    )
"""

import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import EmailLog, SMSLog

logger = logging.getLogger(__name__)


class NotificationService:
    """Service unifié pour les notifications multicanales."""
    
    def __init__(self):
        self.twilio_client = None
        self._init_twilio()
    
    def _init_twilio(self):
        """Initialise le client Twilio si configuré."""
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        
        if account_sid and auth_token:
            try:
                from twilio.rest import Client
                self.twilio_client = Client(account_sid, auth_token)
                logger.info("Twilio client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Twilio: {e}")
    
    def send_notification(self, recipient, message, subject=None, channels=None, 
                          template=None, context=None):
        """
        Envoie une notification via les canaux spécifiés.
        
        Args:
            recipient: Member ou dict avec email, phone, whatsapp_number
            message: Message texte
            subject: Sujet (pour email)
            channels: Liste de canaux ['email', 'sms', 'whatsapp']
            template: Template email (optionnel)
            context: Contexte pour le template
        
        Returns:
            dict: Résultats par canal
        """
        if channels is None:
            channels = self._get_preferred_channels(recipient)
        
        results = {}
        
        for channel in channels:
            try:
                if channel == 'email':
                    results['email'] = self._send_email(
                        recipient, message, subject, template, context
                    )
                elif channel == 'sms':
                    results['sms'] = self._send_sms(recipient, message)
                elif channel == 'whatsapp':
                    results['whatsapp'] = self._send_whatsapp(recipient, message)
                elif channel == 'push':
                    results['push'] = self._send_push(recipient, message)
            except Exception as e:
                logger.error(f"Error sending {channel} notification: {e}")
                results[channel] = {'success': False, 'error': str(e)}
        
        return results
    
    def _get_preferred_channels(self, recipient):
        """Détermine les canaux préférés du destinataire."""
        channels = []
        
        # Si c'est un Member
        if hasattr(recipient, 'notify_by_email') and recipient.notify_by_email:
            if recipient.email:
                channels.append('email')
        
        if hasattr(recipient, 'notify_by_sms') and recipient.notify_by_sms:
            if recipient.phone:
                channels.append('sms')
        
        if hasattr(recipient, 'notify_by_whatsapp') and recipient.notify_by_whatsapp:
            if recipient.whatsapp_number:
                channels.append('whatsapp')
        
        # Par défaut, email si disponible
        if not channels:
            email = getattr(recipient, 'email', None) or recipient.get('email')
            if email:
                channels.append('email')
        
        return channels
    
    def _send_email(self, recipient, message, subject=None, template=None, context=None):
        """Envoie un email."""
        email = getattr(recipient, 'email', None) or recipient.get('email')
        name = getattr(recipient, 'full_name', None) or recipient.get('name', '')
        
        if not email:
            return {'success': False, 'error': 'No email address'}
        
        subject = subject or "Notification EEBC"
        
        # Utiliser un template si fourni
        if template and context:
            html_message = render_to_string(template, context)
        else:
            html_message = None
        
        # Logger l'email
        log = EmailLog.objects.create(
            recipient_email=email,
            recipient_name=name,
            subject=subject,
            body=message
        )
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False
            )
            
            log.status = EmailLog.Status.SENT
            log.sent_at = timezone.now()
            log.save()
            
            return {'success': True, 'log_id': log.id}
        
        except Exception as e:
            log.status = EmailLog.Status.FAILED
            log.error_message = str(e)
            log.save()
            raise
    
    def _send_sms(self, recipient, message):
        """Envoie un SMS via Twilio."""
        phone = getattr(recipient, 'phone', None) or recipient.get('phone')
        name = getattr(recipient, 'full_name', None) or recipient.get('name', '')
        
        if not phone:
            return {'success': False, 'error': 'No phone number'}
        
        if not self.twilio_client:
            return {'success': False, 'error': 'Twilio not configured'}
        
        # Formater le numéro (Guyane: +594)
        phone = self._format_phone_number(phone)
        
        # Logger le SMS
        log = SMSLog.objects.create(
            recipient_phone=phone,
            recipient_name=name,
            message=message
        )
        
        try:
            twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
            
            sms = self.twilio_client.messages.create(
                body=message,
                from_=twilio_phone,
                to=phone
            )
            
            log.status = SMSLog.Status.SENT
            log.save()
            
            return {'success': True, 'sid': sms.sid, 'log_id': log.id}
        
        except Exception as e:
            log.status = SMSLog.Status.FAILED
            log.save()
            raise
    
    def _send_whatsapp(self, recipient, message):
        """Envoie un message WhatsApp via Twilio."""
        whatsapp = getattr(recipient, 'whatsapp_number', None) or recipient.get('whatsapp')
        
        if not whatsapp:
            # Fallback sur le téléphone
            whatsapp = getattr(recipient, 'phone', None) or recipient.get('phone')
        
        if not whatsapp:
            return {'success': False, 'error': 'No WhatsApp number'}
        
        if not self.twilio_client:
            return {'success': False, 'error': 'Twilio not configured'}
        
        # Formater le numéro
        whatsapp = self._format_phone_number(whatsapp)
        
        try:
            twilio_whatsapp = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', None)
            
            msg = self.twilio_client.messages.create(
                body=message,
                from_=f"whatsapp:{twilio_whatsapp}",
                to=f"whatsapp:{whatsapp}"
            )
            
            return {'success': True, 'sid': msg.sid}
        
        except Exception as e:
            raise
    
    def _send_push(self, recipient, message):
        """Envoie une notification push (placeholder pour futur)."""
        # TODO: Implémenter avec Firebase Cloud Messaging ou similaire
        return {'success': False, 'error': 'Push notifications not implemented yet'}
    
    def _format_phone_number(self, phone):
        """Formate un numéro de téléphone pour Twilio."""
        # Nettoyer le numéro
        phone = ''.join(filter(str.isdigit, phone))
        
        # Si le numéro commence par 0, c'est un numéro local Guyane
        if phone.startswith('0'):
            phone = '594' + phone[1:]
        
        # Ajouter le + si absent
        if not phone.startswith('+'):
            phone = '+' + phone
        
        return phone
    
    # =========================================================================
    # MÉTHODES DE NOTIFICATION SPÉCIFIQUES
    # =========================================================================
    
    def send_event_reminder(self, event, recipients=None):
        """Envoie un rappel d'événement."""
        if recipients is None:
            recipients = event.get_notification_recipients()
        
        message = f"""Rappel : {event.title}

Date : {event.start_date.strftime('%d/%m/%Y')}
{f"Heure : {event.start_time.strftime('%H:%M')}" if event.start_time else ""}
{f"Lieu : {event.location}" if event.location else ""}

{event.description[:200] if event.description else ""}

-- 
EEBC - Église Évangélique Baptiste de Cabassou
"""
        
        results = []
        for recipient in recipients:
            result = self.send_notification(
                recipient={'email': recipient},
                message=message,
                subject=f"Rappel : {event.title}"
            )
            results.append(result)
        
        return results
    
    def send_birthday_wishes(self, member):
        """Envoie des vœux d'anniversaire."""
        message = f"""Joyeux anniversaire {member.first_name} ! 🎂

Toute l'église EEBC vous souhaite un merveilleux anniversaire.
Que le Seigneur vous bénisse abondamment en cette nouvelle année de vie.

"L'Éternel te bénisse et te garde !" - Nombres 6:24

Avec toute notre affection,
L'équipe EEBC
"""
        
        return self.send_notification(
            recipient=member,
            message=message,
            subject="Joyeux anniversaire ! 🎂"
        )
    
    def send_absence_alert(self, member, weeks_absent):
        """Envoie une alerte d'absence prolongée (interne)."""
        # Cette notification est pour les responsables, pas le membre
        message = f"""Alerte absence : {member.full_name}

Ce membre n'a pas été vu depuis {weeks_absent} semaines.
Une visite pastorale pourrait être nécessaire.

Téléphone : {member.phone or 'Non renseigné'}
Email : {member.email or 'Non renseigné'}
"""
        
        # Envoyer aux administrateurs
        from apps.accounts.models import User
        admins = User.objects.filter(role__in=['admin', 'secretariat'], is_active=True)
        
        results = []
        for admin in admins:
            if admin.email:
                result = self.send_notification(
                    recipient={'email': admin.email, 'name': admin.get_full_name()},
                    message=message,
                    subject=f"Alerte absence : {member.full_name}",
                    channels=['email']
                )
                results.append(result)
        
        return results
    
    def send_donation_receipt(self, transaction, member):
        """Envoie un reçu de don."""
        message = f"""Reçu de don - EEBC

Cher(e) {member.first_name},

Nous avons bien reçu votre {transaction.get_transaction_type_display().lower()} 
d'un montant de {transaction.amount}€.

Référence : {transaction.reference}
Date : {transaction.transaction_date.strftime('%d/%m/%Y')}
Type : {transaction.get_transaction_type_display()}

Nous vous remercions pour votre générosité et votre soutien à l'œuvre de Dieu.

"Chacun donne comme il l'a résolu en son cœur, sans tristesse ni contrainte ; 
car Dieu aime celui qui donne avec joie." - 2 Corinthiens 9:7

Que Dieu vous bénisse,
EEBC - Église Évangélique Baptiste de Cabassou
"""
        
        return self.send_notification(
            recipient=member,
            message=message,
            subject=f"Reçu de don - {transaction.reference}"
        )


# Import timezone pour les logs
from django.utils import timezone

# Instance singleton pour faciliter l'utilisation
notification_service = NotificationService()
