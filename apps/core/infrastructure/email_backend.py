"""
Infrastructure d'envoi d'emails - Couche technique pure.
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
import logging

from apps.communication.models import EmailLog

logger = logging.getLogger(__name__)


class EmailBackend:
    """
    Backend technique pour l'envoi d'emails.
    Responsabilité unique : envoyer des emails et logger les résultats.
    """
    
    @staticmethod
    def send_email(
        recipient_email: str,
        subject: str,
        html_content: str = None,
        text_content: str = None,
        template_name: str = None,
        context: dict = None,
        recipient_name: str = '',
        from_email: str = None,
        fail_silently: bool = False
    ) -> EmailLog:
        """
        Envoie un email avec gestion du logging.
        
        Args:
            recipient_email: Email du destinataire
            subject: Sujet de l'email
            html_content: Contenu HTML (optionnel si template_name fourni)
            text_content: Contenu texte (optionnel, généré depuis HTML si absent)
            template_name: Nom du template à utiliser (optionnel)
            context: Contexte pour le template
            recipient_name: Nom du destinataire
            from_email: Email expéditeur
            fail_silently: Ne pas lever d'exception en cas d'erreur
            
        Returns:
            EmailLog: Log de l'email envoyé
        """
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        context = context or {}
        
        # Générer le contenu si template fourni
        if template_name and not html_content:
            # Ajouter des variables globales au contexte
            context.update({
                'site_name': 'EEBC',
                'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost',
                'current_year': timezone.now().year,
            })
            html_content = render_to_string(template_name, context)
        
        # Générer le contenu texte si absent
        if html_content and not text_content:
            text_content = strip_tags(html_content)
        
        # Créer le log
        log = EmailLog.objects.create(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body=text_content or html_content,
            status='pending'
        )
        
        try:
            if html_content:
                # Email avec version HTML et texte
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=from_email,
                    to=[recipient_email]
                )
                email.attach_alternative(html_content, "text/html")
                email.send(fail_silently=False)
            else:
                # Email texte simple
                send_mail(
                    subject=subject,
                    message=text_content,
                    from_email=from_email,
                    recipient_list=[recipient_email],
                    fail_silently=False
                )
            
            # Succès
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.save()
            
            logger.info(f"Email envoyé à {recipient_email}: {subject}")
            
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.save()
            
            logger.error(f"Échec envoi email à {recipient_email}: {e}")
            
            if not fail_silently:
                raise
        
        return log
    
    @staticmethod
    def send_bulk_emails(
        recipients: list,
        subject: str,
        html_content: str = None,
        text_content: str = None,
        template_name: str = None,
        context: dict = None,
        from_email: str = None,
        fail_silently: bool = True
    ) -> list:
        """
        Envoie un email à plusieurs destinataires.
        
        Args:
            recipients: Liste de tuples (email, name) ou liste d'emails
            subject: Sujet de l'email
            html_content: Contenu HTML
            text_content: Contenu texte
            template_name: Nom du template
            context: Contexte pour le template
            from_email: Email expéditeur
            fail_silently: Ne pas lever d'exception en cas d'erreur
            
        Returns:
            list: Liste des EmailLog créés
        """
        logs = []
        
        for recipient in recipients:
            if isinstance(recipient, tuple):
                email, name = recipient
            else:
                email, name = recipient, ''
            
            log = EmailBackend.send_email(
                recipient_email=email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                template_name=template_name,
                context=context,
                recipient_name=name,
                from_email=from_email,
                fail_silently=fail_silently
            )
            logs.append(log)
        
        return logs