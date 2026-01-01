"""Signaux pour le module Finance."""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FinancialTransaction


@receiver(post_save, sender=FinancialTransaction)
def notify_large_transaction(sender, instance, created, **kwargs):
    """
    Notifie les administrateurs pour les transactions importantes.
    
    Seuil : 500€ pour les dépenses, 1000€ pour les dons.
    """
    if not created:
        return
    
    threshold = 500 if not instance.is_income else 1000
    
    if instance.amount >= threshold:
        from apps.communication.models import Notification
        from apps.accounts.models import User
        
        # Notifier les trésoriers/admins
        admins = User.objects.filter(is_staff=True, is_active=True)
        
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                title=f"Transaction importante : {instance.reference}",
                message=f"Une {instance.get_transaction_type_display().lower()} de {instance.amount}€ a été enregistrée.",
                notification_type='info',
                link=f"/admin/finance/financialtransaction/{instance.pk}/change/"
            )
