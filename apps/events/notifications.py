"""
Service de notifications pour les événements.
Couche métier - logique spécifique au domaine des événements.
"""
from apps.core.infrastructure.email_backend import EmailBackend


class EventNotificationService:
    """
    Service de notifications spécifique aux événements.
    Contient la logique métier des notifications d'événements.
    """
    
    @staticmethod
    def send_event_notification(event, recipient_email, recipient_name='', days_until=0):
        """
        Notifie d'un événement à venir.
        
        Args:
            event: Instance d'Event
            recipient_email: Email du destinataire
            recipient_name: Nom du destinataire
            days_until: Nombre de jours avant l'événement
            
        Returns:
            EmailLog: Log de l'email envoyé
        """
        context = {
            'event': event,
            'days_until': days_until,
            'recipient_name': recipient_name,
        }
        
        return EmailBackend.send_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=f"📅 Événement à venir : {event.title}",
            template_name='events/emails/event_notification.html',
            context=context
        )
    
    @staticmethod
    def send_event_reminder(event, recipient_email, recipient_name=''):
        """
        Envoie un rappel le jour de l'événement.
        
        Args:
            event: Instance d'Event
            recipient_email: Email du destinataire
            recipient_name: Nom du destinataire
            
        Returns:
            EmailLog: Log de l'email envoyé
        """
        context = {
            'event': event,
            'is_reminder': True,
            'recipient_name': recipient_name,
        }
        
        return EmailBackend.send_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=f"🔔 Rappel : {event.title} - Aujourd'hui !",
            template_name='events/emails/event_reminder.html',
            context=context
        )
    
    @staticmethod
    def send_event_scheduled(event, recipients):
        """
        Notifie qu'un nouvel événement a été planifié.
        
        Args:
            event: Instance d'Event
            recipients: Liste de tuples (email, name)
            
        Returns:
            list[EmailLog]: Liste des logs d'emails envoyés
        """
        context = {
            'event': event,
        }
        
        logs = []
        for email, name in recipients:
            log = EmailBackend.send_email(
                recipient_email=email,
                recipient_name=name,
                subject=f"📌 Nouvel événement : {event.title}",
                template_name='events/emails/event_scheduled.html',
                context={**context, 'recipient_name': name}
            )
            logs.append(log)
        
        return logs
    
    @staticmethod
    def send_event_cancelled(event, recipients, cancellation_reason=''):
        """
        Notifie l'annulation d'un événement.
        
        Args:
            event: Instance d'Event
            recipients: Liste de tuples (email, name)
            cancellation_reason: Raison de l'annulation
            
        Returns:
            list[EmailLog]: Liste des logs d'emails envoyés
        """
        context = {
            'event': event,
            'cancellation_reason': cancellation_reason,
        }
        
        logs = []
        for email, name in recipients:
            log = EmailBackend.send_email(
                recipient_email=email,
                recipient_name=name,
                subject=f"❌ Événement annulé : {event.title}",
                template_name='events/emails/event_cancelled.html',
                context={**context, 'recipient_name': name}
            )
            logs.append(log)
        
        return logs
    
    @staticmethod
    def notify_event_registration(event, registration, confirmation_url=''):
        """
        Confirme l'inscription à un événement.
        
        Args:
            event: Instance d'Event
            registration: Instance d'EventRegistration
            confirmation_url: URL de confirmation (optionnel)
            
        Returns:
            EmailLog: Log de l'email envoyé
        """
        context = {
            'event': event,
            'registration': registration,
            'confirmation_url': confirmation_url,
        }
        
        return EmailBackend.send_email(
            recipient_email=registration.email,
            recipient_name=registration.name,
            subject=f"✅ Inscription confirmée : {event.title}",
            template_name='events/emails/registration_confirmation.html',
            context=context
        )