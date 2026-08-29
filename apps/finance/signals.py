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
        admins = User.objects.filter(role__icontains='finance', is_active=True) | User.objects.filter(role__icontains='admin', is_active=True)
        
        for admin in admins:
            Notification.objects.create(
                user=admin,
                title=f"Transaction importante : {instance.reference}",
                message=f"Une {instance.get_transaction_type_display().lower()} de {instance.amount}€ a été enregistrée.",
                notification_type='info',
                action_url=f"/admin/finance/financialtransaction/{instance.pk}/change/"
            )


@receiver(post_save, sender=FinancialTransaction)
def notify_pending_expense(sender, instance, created, **kwargs):
    """
    Notifie les responsables finance quand une dépense est créée en attente de validation.
    """
    if not created:
        return
    
    if instance.status != 'en_attente':
        return
    
    if instance.transaction_type != 'depense':
        return
    
    from apps.communication.models import Notification
    from apps.accounts.models import User
    from django.db.models import Q
    
    validators = User.objects.filter(
        is_active=True
    ).filter(
        Q(role__icontains='finance') | Q(role__icontains='admin') | Q(is_superuser=True)
    ).distinct()
    
    recorded_by = instance.recorded_by.get_full_name() if instance.recorded_by else 'Inconnu'
    
    for user in validators:
        Notification.objects.create(
            user=user,
            title=f"💳 Dépense à valider : {instance.amount}€",
            message=(
                f"Une dépense de {instance.amount}€ est en attente de validation.\n"
                f"Référence : {instance.reference}\n"
                f"Description : {instance.description[:100] if instance.description else 'Aucune'}\n"
                f"Enregistrée par : {recorded_by}"
            ),
            notification_type='warning',
            action_url=f"/app/finance/transactions/{instance.pk}/",
        )
