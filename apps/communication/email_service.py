"""
Service centralisé d'envoi d'emails pour EEBC.
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
import logging

from .models import EmailLog

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service centralisé pour l'envoi d'emails.
    Gère le logging, les templates et les erreurs.
    """
    
    @staticmethod
    def send(
        recipient_email: str,
        subject: str,
        template_name: str,
        context: dict = None,
        recipient_name: str = '',
        from_email: str = None,
        fail_silently: bool = False
    ) -> EmailLog:
        """
        Envoie un email avec template HTML.
        
        Args:
            recipient_email: Email du destinataire
            subject: Sujet de l'email
            template_name: Chemin du template (ex: 'communication/email/base.html')
            context: Contexte pour le template
            recipient_name: Nom du destinataire (optionnel)
            from_email: Email expéditeur (utilise DEFAULT_FROM_EMAIL si non fourni)
            fail_silently: Ne pas lever d'exception en cas d'erreur
            
        Returns:
            EmailLog: Log de l'email envoyé
        """
        context = context or {}
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        
        # Ajouter des variables globales au contexte
        context.update({
            'site_name': 'EEBC',
            'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost',
            'current_year': timezone.now().year,
        })
        
        # Générer le contenu HTML et texte
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)
        
        # Créer le log
        log = EmailLog.objects.create(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body=text_content,
            status='pending'
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
            email.send(fail_silently=False)
            
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
    def send_bulk(
        recipients: list,
        subject: str,
        template_name: str,
        context: dict = None,
        fail_silently: bool = True
    ) -> list:
        """
        Envoie un email à plusieurs destinataires.
        
        Args:
            recipients: Liste de tuples (email, name) ou liste d'emails
            subject: Sujet de l'email
            template_name: Chemin du template
            context: Contexte pour le template
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
            
            log = EmailService.send(
                recipient_email=email,
                subject=subject,
                template_name=template_name,
                context=context,
                recipient_name=name,
                fail_silently=fail_silently
            )
            logs.append(log)
        
        return logs


# =============================================================================
# FONCTIONS UTILITAIRES SPÉCIALISÉES
# =============================================================================

def send_absence_notification(child, session, parent_email, parent_name=''):
    """
    Notifie un parent de l'absence de son enfant au Club Biblique.
    """
    context = {
        'child': child,
        'session': session,
        'parent_name': parent_name,
    }
    
    return EmailService.send(
        recipient_email=parent_email,
        subject=f"Absence de {child.first_name} - Club Biblique EEBC",
        template_name='communication/email/absence_notification.html',
        context=context,
        recipient_name=parent_name
    )


def notify_parents_of_absence(child, session):
    """
    Notifie tous les parents d'un enfant de son absence.
    
    Returns:
        list[EmailLog]: Liste des logs d'emails envoyés
    """
    logs = []
    
    if child.father_email:
        log = send_absence_notification(child, session, child.father_email, child.father_name)
        logs.append(log)
    
    if child.mother_email:
        log = send_absence_notification(child, session, child.mother_email, child.mother_name)
        logs.append(log)
    
    return logs


def send_event_notification(event, recipient_email, recipient_name='', days_until=0):
    """
    Notifie d'un événement à venir.
    """
    context = {
        'event': event,
        'days_until': days_until,
        'recipient_name': recipient_name,
    }
    
    return EmailService.send(
        recipient_email=recipient_email,
        subject=f"📅 Événement à venir : {event.title}",
        template_name='events/email/event_notification.html',
        context=context,
        recipient_name=recipient_name
    )


def send_event_reminder(event, recipient_email, recipient_name=''):
    """
    Envoie un rappel le jour de l'événement.
    """
    context = {
        'event': event,
        'is_reminder': True,
        'recipient_name': recipient_name,
    }
    
    return EmailService.send(
        recipient_email=recipient_email,
        subject=f"🔔 Rappel : {event.title} - Aujourd'hui !",
        template_name='events/email/event_reminder.html',
        context=context,
        recipient_name=recipient_name
    )


def send_campaign_notification(campaign, donation, donor_email, donor_name=''):
    """
    Remercie un donateur pour sa contribution à une campagne.
    """
    context = {
        'campaign': campaign,
        'donation': donation,
        'donor_name': donor_name,
    }
    
    return EmailService.send(
        recipient_email=donor_email,
        subject=f"Merci pour votre don - {campaign.name}",
        template_name='communication/email/donation_thanks.html',
        context=context,
        recipient_name=donor_name
    )


def send_welcome_email(user):
    """
    Envoie un email de bienvenue à un nouvel utilisateur.
    """
    context = {
        'user': user,
    }
    
    return EmailService.send(
        recipient_email=user.email,
        subject="Bienvenue sur EEBC !",
        template_name='communication/email/welcome.html',
        context=context,
        recipient_name=user.get_full_name()
    )


def send_password_reset(user, reset_url):
    """
    Envoie un email de réinitialisation de mot de passe.
    """
    context = {
        'user': user,
        'reset_url': reset_url,
    }
    
    return EmailService.send(
        recipient_email=user.email,
        subject="Réinitialisation de votre mot de passe - EEBC",
        template_name='communication/email/password_reset.html',
        context=context,
        recipient_name=user.get_full_name()
    )


def send_event_scheduled(event, recipient_email, recipient_name=''):
    """
    Notifie qu'un nouvel événement a été planifié.
    """
    context = {
        'event': event,
        'recipient_name': recipient_name,
    }
    
    return EmailService.send(
        recipient_email=recipient_email,
        subject=f"📌 Nouvel événement : {event.title}",
        template_name='communication/email/event_scheduled.html',
        context=context,
        recipient_name=recipient_name
    )


def send_event_cancelled(event, recipient_email, recipient_name='', cancellation_reason=''):
    """
    Notifie l'annulation d'un événement.
    """
    context = {
        'event': event,
        'recipient_name': recipient_name,
        'cancellation_reason': cancellation_reason,
    }
    
    return EmailService.send(
        recipient_email=recipient_email,
        subject=f"❌ Événement annulé : {event.title}",
        template_name='communication/email/event_cancelled.html',
        context=context,
        recipient_name=recipient_name
    )


def send_session_completed(session, recipient_email, recipient_name='', stats=None):
    """
    Notifie qu'une session du Club Biblique est terminée avec les stats.
    """
    if stats is None:
        # Calculer les stats si non fournies
        from apps.bibleclub.models import Attendance
        attendances = Attendance.objects.filter(session=session)
        present = attendances.filter(is_present=True).count()
        absent = attendances.filter(is_present=False).count()
        total = present + absent
        stats = {
            'present': present,
            'absent': absent,
            'total': total,
            'attendance_rate': round((present / total * 100) if total > 0 else 0),
        }
    
    context = {
        'session': session,
        'recipient_name': recipient_name,
        'stats': stats,
    }
    
    return EmailService.send(
        recipient_email=recipient_email,
        subject=f"✅ Appel terminé - {session.bible_class.name} ({session.date})",
        template_name='communication/email/session_completed.html',
        context=context,
        recipient_name=recipient_name
    )


def send_recurring_absence(child, absences, parent_email, parent_name=''):
    """
    Notifie un parent des absences récurrentes de son enfant (3+ absences).
    """
    context = {
        'child': child,
        'absences': absences,
        'absence_count': len(absences) if hasattr(absences, '__len__') else absences.count(),
        'parent_name': parent_name,
    }
    
    return EmailService.send(
        recipient_email=parent_email,
        subject=f"⚠️ Absences récurrentes de {child.first_name} - Club Biblique",
        template_name='communication/email/recurring_absence.html',
        context=context,
        recipient_name=parent_name
    )


def check_and_notify_recurring_absences(child, threshold=3):
    """
    Vérifie si un enfant a des absences récurrentes et notifie les parents.
    
    Args:
        child: Instance de Child
        threshold: Nombre d'absences consécutives pour déclencher la notification
        
    Returns:
        list[EmailLog] ou liste vide si pas de notification envoyée
    """
    from apps.bibleclub.models import Attendance
    
    # Récupérer les dernières présences
    recent_attendances = Attendance.objects.filter(
        child=child
    ).order_by('-session__date')[:threshold]
    
    # Vérifier si toutes sont des absences
    if recent_attendances.count() >= threshold:
        all_absent = all(att.status in ['absent', 'absent_notified'] for att in recent_attendances)
        
        if all_absent:
            logs = []
            
            # Notifier le père si email disponible
            if child.father_email:
                log = send_recurring_absence(
                    child=child,
                    absences=recent_attendances,
                    parent_email=child.father_email,
                    parent_name=child.father_name
                )
                logs.append(log)
            
            # Notifier la mère si email disponible
            if child.mother_email:
                log = send_recurring_absence(
                    child=child,
                    absences=recent_attendances,
                    parent_email=child.mother_email,
                    parent_name=child.mother_name
                )
                logs.append(log)
            
            return logs
    
    return []


def get_parent_emails(child):
    """
    Récupère les emails des parents d'un enfant.
    
    Returns:
        list: Liste de tuples (email, nom)
    """
    emails = []
    if child.father_email:
        emails.append((child.father_email, child.father_name))
    if child.mother_email:
        emails.append((child.mother_email, child.mother_name))
    return emails
