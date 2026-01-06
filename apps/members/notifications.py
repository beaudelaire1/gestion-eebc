"""
Service de notifications pour les membres.
Couche métier - logique spécifique au domaine des membres.
"""
from apps.core.infrastructure.email_backend import EmailBackend


class MemberNotificationService:
    """
    Service de notifications spécifique aux membres.
    Contient la logique métier des notifications membres.
    """
    
    @staticmethod
    def send_welcome_email(user):
        """
        Envoie un email de bienvenue à un nouvel utilisateur.
        
        Args:
            user: Instance de User
            
        Returns:
            EmailLog: Log de l'email envoyé
        """
        context = {
            'user': user,
            'member': getattr(user, 'member_profile', None),
        }
        
        return EmailBackend.send_email(
            recipient_email=user.email,
            recipient_name=user.get_full_name(),
            subject="Bienvenue sur EEBC !",
            template_name='members/emails/welcome.html',
            context=context
        )
    
    @staticmethod
    def send_password_reset(user, reset_url):
        """
        Envoie un email de réinitialisation de mot de passe.
        
        Args:
            user: Instance de User
            reset_url: URL de réinitialisation
            
        Returns:
            EmailLog: Log de l'email envoyé
        """
        context = {
            'user': user,
            'reset_url': reset_url,
        }
        
        return EmailBackend.send_email(
            recipient_email=user.email,
            recipient_name=user.get_full_name(),
            subject="Réinitialisation de votre mot de passe - EEBC",
            template_name='members/emails/password_reset.html',
            context=context
        )
    
    @staticmethod
    def notify_life_event(life_event, recipients):
        """
        Notifie un événement de vie aux personnes concernées.
        
        Args:
            life_event: Instance de LifeEvent
            recipients: Liste de tuples (email, name)
            
        Returns:
            list[EmailLog]: Liste des logs d'emails envoyés
        """
        context = {
            'life_event': life_event,
            'member': life_event.primary_member,
            'event_type': life_event.get_event_type_display(),
        }
        
        logs = []
        for email, name in recipients:
            log = EmailBackend.send_email(
                recipient_email=email,
                recipient_name=name,
                subject=f"Événement de vie - {life_event.title}",
                template_name='members/emails/life_event_notification.html',
                context={**context, 'recipient_name': name}
            )
            logs.append(log)
        
        return logs
    
    @staticmethod
    def notify_visit_scheduled(visit, recipient_email, recipient_name=''):
        """
        Notifie qu'une visite pastorale a été programmée.
        
        Args:
            visit: Instance de VisitationLog
            recipient_email: Email du destinataire
            recipient_name: Nom du destinataire
            
        Returns:
            EmailLog: Log de l'email envoyé
        """
        context = {
            'visit': visit,
            'member': visit.member,
            'visitor': visit.visitor,
        }
        
        return EmailBackend.send_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=f"Visite pastorale programmée - {visit.member.full_name}",
            template_name='members/emails/visit_scheduled.html',
            context={**context, 'recipient_name': recipient_name}
        )
    
    @staticmethod
    def notify_visit_completed(visit, recipient_email, recipient_name=''):
        """
        Notifie qu'une visite pastorale a été effectuée.
        
        Args:
            visit: Instance de VisitationLog
            recipient_email: Email du destinataire
            recipient_name: Nom du destinataire
            
        Returns:
            EmailLog: Log de l'email envoyé
        """
        context = {
            'visit': visit,
            'member': visit.member,
            'visitor': visit.visitor,
        }
        
        return EmailBackend.send_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=f"Visite pastorale effectuée - {visit.member.full_name}",
            template_name='members/emails/visit_completed.html',
            context={**context, 'recipient_name': recipient_name}
        )