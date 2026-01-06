"""
Service centralisé pour l'envoi d'emails et notifications - EEBC.

Ce service gère l'envoi d'emails avec templates configurables,
le logging automatique et les notifications d'événements.
"""
import logging
from typing import List, Dict, Optional, Union
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template import Template, Context
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import EmailLog, EmailTemplate

logger = logging.getLogger(__name__)
User = get_user_model()


class EmailService:
    """
    Service centralisé pour l'envoi d'emails avec logging automatique.
    
    Fonctionnalités:
    - Envoi d'emails avec templates HTML
    - Templates configurables depuis l'admin Django
    - Logging automatique de tous les envois
    - Gestion des erreurs
    - Support des emails en masse
    """
    
    @staticmethod
    def send_email_with_template(
        recipient_email: str,
        template_type: str,
        context: Optional[Dict] = None,
        template_name: Optional[str] = None,
        recipient_name: str = '',
        from_email: Optional[str] = None,
        fail_silently: bool = False
    ) -> EmailLog:
        """
        Envoie un email en utilisant un template configurable depuis l'admin.
        
        Args:
            recipient_email: Email du destinataire
            template_type: Type de template (EmailTemplate.TemplateType)
            context: Variables pour le template
            template_name: Nom spécifique du template (optionnel)
            recipient_name: Nom du destinataire (optionnel)
            from_email: Email expéditeur (utilise DEFAULT_FROM_EMAIL si non fourni)
            fail_silently: Ne pas lever d'exception en cas d'erreur
            
        Returns:
            EmailLog: Instance du log créé
        """
        context = context or {}
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        
        # Enrichir le contexte avec des variables globales
        context.update({
            'site_name': 'EEBC - Église Évangélique Baptiste de Cabassou',
            'site_url': getattr(settings, 'SITE_URL', 'https://eebc-guyane.org'),
            'current_year': timezone.now().year,
            'contact_email': getattr(settings, 'CONTACT_EMAIL', 'contact@eebc-guyane.org'),
            'recipient_name': recipient_name,
        })
        
        # Récupérer le template depuis la base de données
        email_template = EmailTemplate.get_template_by_type(template_type, template_name)
        
        if not email_template:
            # Fallback sur template par défaut
            logger.warning(f"Aucun template trouvé pour {template_type}, utilisation du fallback")
            return EmailService.send_email(
                recipient_email=recipient_email,
                subject=f"Notification EEBC",
                template_name='emails/default.html',
                context=context,
                recipient_name=recipient_name,
                from_email=from_email,
                fail_silently=fail_silently
            )
        
        # Générer le sujet avec le contexte
        try:
            subject_template = Template(email_template.subject)
            subject = subject_template.render(Context(context))
        except Exception as e:
            logger.error(f"Erreur génération sujet template {email_template.name}: {e}")
            subject = email_template.subject  # Utiliser le sujet brut
        
        # Générer le contenu HTML avec le contexte
        try:
            html_template = Template(email_template.html_content)
            html_content = html_template.render(Context(context))
        except Exception as e:
            logger.error(f"Erreur génération HTML template {email_template.name}: {e}")
            html_content = f"<p>Erreur de template: {e}</p>"
        
        # Générer le contenu texte
        if email_template.text_content:
            try:
                text_template = Template(email_template.text_content)
                text_content = text_template.render(Context(context))
            except Exception as e:
                logger.error(f"Erreur génération texte template {email_template.name}: {e}")
                text_content = strip_tags(html_content)
        else:
            text_content = strip_tags(html_content)
        
        # Créer le log d'email
        email_log = EmailLog.objects.create(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body=text_content,
            template_type=template_type,
            status=EmailLog.Status.PENDING
        )
        
        try:
            # Créer l'email avec version HTML et texte
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[recipient_email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Envoyer l'email
            email.send(fail_silently=False)
            
            # Marquer comme envoyé
            email_log.status = EmailLog.Status.SENT
            email_log.sent_at = timezone.now()
            email_log.save()
            
            logger.info(f"Email envoyé avec template {email_template.name} à {recipient_email}: {subject}")
            
        except Exception as e:
            # Marquer comme échoué
            email_log.status = EmailLog.Status.FAILED
            email_log.error_message = str(e)
            email_log.save()
            
            logger.error(f"Échec envoi email template {email_template.name} à {recipient_email}: {e}")
            
            if not fail_silently:
                raise
        
        return email_log
    
    @staticmethod
    def send_email(
        recipient_email: str,
        subject: str,
        template_name: str,
        context: Optional[Dict] = None,
        recipient_name: str = '',
        from_email: Optional[str] = None,
        fail_silently: bool = False
    ) -> EmailLog:
        """
        Envoie un email avec template HTML et logging automatique.
        
        Args:
            recipient_email: Email du destinataire
            subject: Sujet de l'email
            template_name: Chemin du template (ex: 'emails/event_notification.html')
            context: Variables pour le template
            recipient_name: Nom du destinataire (optionnel)
            from_email: Email expéditeur (utilise DEFAULT_FROM_EMAIL si non fourni)
            fail_silently: Ne pas lever d'exception en cas d'erreur
            
        Returns:
            EmailLog: Instance du log créé
            
        Raises:
            Exception: Si fail_silently=False et erreur d'envoi
        """
        context = context or {}
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        
        # Enrichir le contexte avec des variables globales
        context.update({
            'site_name': 'EEBC - Église Évangélique Baptiste de Cabassou',
            'site_url': getattr(settings, 'SITE_URL', 'https://eebc-guyane.org'),
            'current_year': timezone.now().year,
            'contact_email': getattr(settings, 'CONTACT_EMAIL', 'contact@eebc-guyane.org'),
        })
        
        # Générer le contenu HTML et texte
        try:
            html_content = render_to_string(template_name, context)
            text_content = strip_tags(html_content)
        except Exception as e:
            logger.error(f"Erreur génération template {template_name}: {e}")
            # Fallback sur message texte simple
            text_content = f"Sujet: {subject}\n\nMessage depuis EEBC"
            html_content = f"<p>{text_content}</p>"
        
        # Créer le log d'email
        email_log = EmailLog.objects.create(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body=text_content,
            status=EmailLog.Status.PENDING
        )
        
        try:
            # Créer l'email avec version HTML et texte
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[recipient_email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Envoyer l'email
            email.send(fail_silently=False)
            
            # Marquer comme envoyé
            email_log.status = EmailLog.Status.SENT
            email_log.sent_at = timezone.now()
            email_log.save()
            
            logger.info(f"Email envoyé avec succès à {recipient_email}: {subject}")
            
        except Exception as e:
            # Marquer comme échoué
            email_log.status = EmailLog.Status.FAILED
            email_log.error_message = str(e)
            email_log.save()
            
            logger.error(f"Échec envoi email à {recipient_email}: {e}")
            
            if not fail_silently:
                raise
        
        return email_log
    
    @staticmethod
    def send_bulk_emails(
        recipients: List[Union[str, tuple]],
        subject: str,
        template_name: str,
        context: Optional[Dict] = None,
        fail_silently: bool = True
    ) -> List[EmailLog]:
        """
        Envoie un email à plusieurs destinataires.
        
        Args:
            recipients: Liste d'emails ou tuples (email, nom)
            subject: Sujet de l'email
            template_name: Chemin du template
            context: Variables pour le template
            fail_silently: Ne pas lever d'exception en cas d'erreur
            
        Returns:
            List[EmailLog]: Liste des logs créés
        """
        logs = []
        
        for recipient in recipients:
            if isinstance(recipient, tuple):
                email, name = recipient
            else:
                email, name = recipient, ''
            
            try:
                log = EmailService.send_email(
                    recipient_email=email,
                    subject=subject,
                    template_name=template_name,
                    context=context,
                    recipient_name=name,
                    fail_silently=fail_silently
                )
                logs.append(log)
            except Exception as e:
                logger.error(f"Erreur envoi email bulk à {email}: {e}")
                if not fail_silently:
                    raise
        
        return logs


class NotificationService:
    """
    Service de notifications pour les événements et rappels.
    
    Gère l'envoi de notifications automatiques pour:
    - Événements à venir
    - Rappels d'événements
    - Annulations d'événements
    - Notifications de transport
    """
    
    @staticmethod
    def send_event_notification(
        event,
        recipients: Optional[List] = None,
        notification_type: str = 'upcoming'
    ) -> List[EmailLog]:
        """
        Envoie une notification d'événement en utilisant les templates configurables.
        
        Args:
            event: Instance d'Event
            recipients: Liste d'emails ou None pour utiliser les inscrits
            notification_type: Type de notification ('upcoming', 'reminder', 'cancelled')
            
        Returns:
            List[EmailLog]: Liste des logs d'emails envoyés
        """
        if recipients is None:
            recipients = NotificationService._get_event_recipients(event)
        
        # Mapper les types de notification aux types de templates
        template_types = {
            'upcoming': 'event_notification',
            'reminder': 'event_reminder',
            'cancelled': 'event_cancelled'
        }
        
        template_type = template_types.get(notification_type, 'event_notification')
        
        # Contexte pour le template
        context = {
            'event': event,
            'notification_type': notification_type,
            'is_reminder': notification_type == 'reminder',
            'is_cancelled': notification_type == 'cancelled',
        }
        
        # Envoyer à tous les destinataires
        logs = []
        for recipient in recipients:
            if isinstance(recipient, dict):
                email = recipient.get('email')
                name = recipient.get('name', '')
            elif hasattr(recipient, 'email'):
                email = recipient.email
                name = getattr(recipient, 'get_full_name', lambda: '')() or str(recipient)
            else:
                email = str(recipient)
                name = ''
            
            if email:
                try:
                    # Utiliser le service d'email avec template configurable
                    log = EmailService.send_email_with_template(
                        recipient_email=email,
                        template_type=template_type,
                        context=context,
                        recipient_name=name,
                        fail_silently=True
                    )
                    logs.append(log)
                except Exception as e:
                    logger.error(f"Erreur notification événement à {email}: {e}")
        
        logger.info(f"Notification événement '{event.title}' envoyée à {len(logs)} destinataires")
        return logs
        logs = []
        for recipient in recipients:
            if isinstance(recipient, dict):
                email = recipient.get('email')
                name = recipient.get('name', '')
            elif hasattr(recipient, 'email'):
                email = recipient.email
                name = getattr(recipient, 'get_full_name', lambda: '')() or str(recipient)
            else:
                email = str(recipient)
                name = ''
            
            if email:
                try:
                    # Ajouter le nom du destinataire au contexte
                    recipient_context = context.copy()
                    recipient_context['recipient_name'] = name
                    
                    log = EmailService.send_email(
                        recipient_email=email,
                        subject=subject,
                        template_name=template_name,
                        context=recipient_context,
                        recipient_name=name,
                        fail_silently=True
                    )
                    logs.append(log)
                except Exception as e:
                    logger.error(f"Erreur notification événement à {email}: {e}")
        
        logger.info(f"Notification événement '{event.title}' envoyée à {len(logs)} destinataires")
        return logs
    
    @staticmethod
    def send_reminder(
        event,
        recipients: Optional[List] = None,
        days_before: int = 0
    ) -> List[EmailLog]:
        """
        Envoie un rappel d'événement en utilisant les templates configurables.
        
        Args:
            event: Instance d'Event
            recipients: Liste d'emails ou None pour utiliser les inscrits
            days_before: Nombre de jours avant l'événement (0 = jour même)
            
        Returns:
            List[EmailLog]: Liste des logs d'emails envoyés
        """
        if recipients is None:
            recipients = NotificationService._get_event_recipients(event)
        
        # Contexte pour le template de rappel
        context = {
            'event': event,
            'days_before': days_before,
            'is_today': days_before == 0,
            'is_tomorrow': days_before == 1,
        }
        
        # Envoyer les rappels en utilisant le template configurable
        logs = []
        for recipient in recipients:
            if isinstance(recipient, dict):
                email = recipient.get('email')
                name = recipient.get('name', '')
            elif hasattr(recipient, 'email'):
                email = recipient.email
                name = getattr(recipient, 'get_full_name', lambda: '')() or str(recipient)
            else:
                email = str(recipient)
                name = ''
            
            if email:
                try:
                    # Utiliser le service d'email avec template configurable
                    log = EmailService.send_email_with_template(
                        recipient_email=email,
                        template_type='event_reminder',
                        context=context,
                        recipient_name=name,
                        fail_silently=True
                    )
                    logs.append(log)
                except Exception as e:
                    logger.error(f"Erreur rappel événement à {email}: {e}")
        
        logger.info(f"Rappel événement '{event.title}' envoyé à {len(logs)} destinataires")
        return logs
    
    @staticmethod
    def _get_event_recipients(event) -> List[Dict]:
        """
        Récupère la liste des destinataires pour un événement.
        
        Args:
            event: Instance d'Event
            
        Returns:
            List[Dict]: Liste de dictionnaires {'email': str, 'name': str}
        """
        recipients = []
        
        # Si l'événement a des inscrits
        if hasattr(event, 'registrations'):
            for registration in event.registrations.filter(is_active=True):
                if hasattr(registration, 'member') and registration.member.email:
                    recipients.append({
                        'email': registration.member.email,
                        'name': registration.member.get_full_name()
                    })
        
        # Si pas d'inscrits, utiliser tous les membres actifs avec email
        if not recipients:
            try:
                from apps.members.models import Member
                members = Member.objects.filter(
                    is_active=True,
                    email__isnull=False
                ).exclude(email='')
                
                for member in members:
                    recipients.append({
                        'email': member.email,
                        'name': member.get_full_name()
                    })
            except Exception as e:
                logger.warning(f"Impossible de récupérer les membres: {e}")
        
        # Fallback: utiliser tous les utilisateurs actifs
        if not recipients:
            users = User.objects.filter(
                is_active=True,
                email__isnull=False
            ).exclude(email='')
            
            for user in users:
                recipients.append({
                    'email': user.email,
                    'name': user.get_full_name()
                })
        
        return recipients
    
    @staticmethod
    def send_transport_confirmation(
        transport_request,
        driver=None,
        passenger_email=None
    ) -> Optional[EmailLog]:
        """
        Envoie une confirmation de transport.
        
        Args:
            transport_request: Instance de TransportRequest
            driver: Instance de Driver assigné (optionnel)
            passenger_email: Email du passager (optionnel)
            
        Returns:
            EmailLog ou None si pas d'email
        """
        # Déterminer l'email du destinataire
        email = passenger_email
        if not email and hasattr(transport_request, 'requester'):
            email = transport_request.requester.email
        if not email and hasattr(transport_request, 'passenger_email'):
            email = transport_request.passenger_email
        
        if not email:
            logger.warning("Aucun email trouvé pour la confirmation de transport")
            return None
        
        # Déterminer le nom du destinataire
        name = ''
        if hasattr(transport_request, 'requester'):
            name = transport_request.requester.get_full_name()
        elif hasattr(transport_request, 'passenger_name'):
            name = transport_request.passenger_name
        
        context = {
            'transport_request': transport_request,
            'driver': driver,
            'has_driver': driver is not None,
            'recipient_name': name,
        }
        
        subject = f"🚗 Confirmation de transport - {transport_request.destination}"
        
        try:
            log = EmailService.send_email(
                recipient_email=email,
                subject=subject,
                template_name='emails/transport_confirmation.html',
                context=context,
                recipient_name=name,
                fail_silently=False
            )
            
            logger.info(f"Confirmation transport envoyée à {email}")
            return log
            
        except Exception as e:
            logger.error(f"Erreur envoi confirmation transport à {email}: {e}")
            return None


# Fonctions utilitaires pour faciliter l'utilisation

def send_event_notification(event, recipients=None, notification_type='upcoming'):
    """Raccourci pour envoyer une notification d'événement."""
    return NotificationService.send_event_notification(event, recipients, notification_type)


def send_event_reminder(event, recipients=None, days_before=0):
    """Raccourci pour envoyer un rappel d'événement."""
    return NotificationService.send_reminder(event, recipients, days_before)


def send_email(recipient_email, subject, template_name, context=None, **kwargs):
    """Raccourci pour envoyer un email simple."""
    return EmailService.send_email(recipient_email, subject, template_name, context, **kwargs)


def send_bulk_emails(recipients, subject, template_name, context=None, **kwargs):
    """Raccourci pour envoyer des emails en masse."""
    return EmailService.send_bulk_emails(recipients, subject, template_name, context, **kwargs)