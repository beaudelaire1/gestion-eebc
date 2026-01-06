"""
Signals pour le logging automatique des actions sensibles.

Ce module contient les signals Django pour:
- Logger les modifications de données sensibles (Member, FinancialTransaction)
- Logger les connexions/déconnexions
- Logger les suppressions

Requirements: 8.2, 8.3
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed

# Thread-local storage pour stocker le contexte de la requête
import threading
_thread_locals = threading.local()


def get_current_request():
    """Récupère la requête courante depuis le thread local."""
    return getattr(_thread_locals, 'request', None)


def set_current_request(request):
    """Stocke la requête courante dans le thread local."""
    _thread_locals.request = request


def clear_current_request():
    """Efface la requête courante du thread local."""
    if hasattr(_thread_locals, 'request'):
        del _thread_locals.request


class AuditMiddleware:
    """
    Middleware pour stocker la requête courante dans le thread local.
    Permet aux signals d'accéder au contexte de la requête.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        set_current_request(request)
        try:
            response = self.get_response(request)
        finally:
            clear_current_request()
        return response


# =============================================================================
# SIGNALS POUR LES MODÈLES SENSIBLES
# =============================================================================

# Liste des modèles à auditer automatiquement
AUDITED_MODELS = [
    'members.Member',
    'finance.FinancialTransaction',
    'finance.Budget',
    'accounts.User',
]


def get_model_changes(instance, created):
    """
    Calcule les changements entre l'ancienne et la nouvelle version d'un objet.
    
    Args:
        instance: L'instance du modèle
        created: True si c'est une création
    
    Returns:
        dict: Dictionnaire des changements {field: {'old': x, 'new': y}}
    """
    if created:
        return {'_created': True}
    
    changes = {}
    
    # Récupérer l'ancienne version depuis la base de données
    try:
        old_instance = instance.__class__.objects.get(pk=instance.pk)
    except instance.__class__.DoesNotExist:
        return {'_created': True}
    
    # Comparer les champs
    for field in instance._meta.fields:
        field_name = field.name
        
        # Ignorer certains champs
        if field_name in ['updated_at', 'created_at', 'last_login', 'password']:
            continue
        
        old_value = getattr(old_instance, field_name, None)
        new_value = getattr(instance, field_name, None)
        
        # Convertir les valeurs pour la comparaison
        if hasattr(old_value, 'pk'):
            old_value = old_value.pk
        if hasattr(new_value, 'pk'):
            new_value = new_value.pk
        
        if old_value != new_value:
            changes[field_name] = {
                'old': str(old_value) if old_value is not None else None,
                'new': str(new_value) if new_value is not None else None
            }
    
    return changes


def should_audit_model(sender):
    """Vérifie si un modèle doit être audité."""
    model_path = f"{sender._meta.app_label}.{sender._meta.object_name}"
    return model_path in AUDITED_MODELS


@receiver(pre_save)
def store_old_instance(sender, instance, **kwargs):
    """
    Stocke l'ancienne version de l'instance avant la sauvegarde.
    Utilisé pour calculer les changements.
    """
    if not should_audit_model(sender):
        return
    
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_instance = old_instance
        except sender.DoesNotExist:
            instance._old_instance = None
    else:
        instance._old_instance = None


@receiver(post_save)
def audit_model_save(sender, instance, created, **kwargs):
    """
    Signal pour logger les créations et modifications de modèles sensibles.
    
    Requirements: 8.3
    """
    if not should_audit_model(sender):
        return
    
    # Éviter l'import circulaire
    from apps.core.models import AuditLog
    
    # Déterminer l'action
    action = AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
    
    # Calculer les changements
    changes = {}
    if not created and hasattr(instance, '_old_instance') and instance._old_instance:
        old_instance = instance._old_instance
        for field in instance._meta.fields:
            field_name = field.name
            
            # Ignorer certains champs sensibles ou techniques
            if field_name in ['updated_at', 'created_at', 'last_login', 'password', 
                              'two_factor_secret', 'two_factor_backup_codes']:
                continue
            
            old_value = getattr(old_instance, field_name, None)
            new_value = getattr(instance, field_name, None)
            
            # Convertir les FK en leur PK pour comparaison
            if hasattr(old_value, 'pk'):
                old_value = old_value.pk
            if hasattr(new_value, 'pk'):
                new_value = new_value.pk
            
            if old_value != new_value:
                changes[field_name] = {
                    'old': str(old_value) if old_value is not None else None,
                    'new': str(new_value) if new_value is not None else None
                }
    
    # Récupérer le contexte de la requête
    request = get_current_request()
    
    # Créer l'entrée d'audit
    if request:
        AuditLog.log_from_request(
            request=request,
            action=action,
            model_name=f"{sender._meta.app_label}.{sender._meta.object_name}",
            object_id=instance.pk,
            object_repr=str(instance),
            changes=changes
        )
    else:
        # Pas de requête (ex: commande manage.py, tâche Celery)
        AuditLog.log(
            action=action,
            model_name=f"{sender._meta.app_label}.{sender._meta.object_name}",
            object_id=instance.pk,
            object_repr=str(instance),
            changes=changes,
            extra_data={'source': 'background_task'}
        )


@receiver(post_delete)
def audit_model_delete(sender, instance, **kwargs):
    """
    Signal pour logger les suppressions de modèles sensibles.
    
    Requirements: 8.3
    """
    if not should_audit_model(sender):
        return
    
    # Éviter l'import circulaire
    from apps.core.models import AuditLog
    
    # Récupérer le contexte de la requête
    request = get_current_request()
    
    # Préparer les données de l'objet supprimé
    deleted_data = {}
    for field in instance._meta.fields:
        field_name = field.name
        if field_name not in ['password', 'two_factor_secret', 'two_factor_backup_codes']:
            value = getattr(instance, field_name, None)
            if hasattr(value, 'pk'):
                value = value.pk
            deleted_data[field_name] = str(value) if value is not None else None
    
    # Créer l'entrée d'audit
    if request:
        AuditLog.log_from_request(
            request=request,
            action=AuditLog.Action.DELETE,
            model_name=f"{sender._meta.app_label}.{sender._meta.object_name}",
            object_id=instance.pk,
            object_repr=str(instance),
            changes={'_deleted_data': deleted_data}
        )
    else:
        AuditLog.log(
            action=AuditLog.Action.DELETE,
            model_name=f"{sender._meta.app_label}.{sender._meta.object_name}",
            object_id=instance.pk,
            object_repr=str(instance),
            changes={'_deleted_data': deleted_data},
            extra_data={'source': 'background_task'}
        )



# =============================================================================
# SIGNALS POUR LES CONNEXIONS/DÉCONNEXIONS
# =============================================================================

@receiver(user_logged_in)
def audit_user_login(sender, request, user, **kwargs):
    """
    Signal pour logger les connexions réussies.
    
    Requirements: 8.2
    """
    from apps.core.models import AuditLog
    
    # Extraire l'IP et le User-Agent manuellement car request.user peut ne pas être défini
    ip_address = AuditLog.get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    AuditLog.log(
        action=AuditLog.Action.LOGIN,
        user=user,
        model_name='accounts.User',
        object_id=user.pk,
        object_repr=str(user),
        ip_address=ip_address,
        user_agent=user_agent,
        path=request.path,
        extra_data={
            'username': user.username,
            'email': user.email,
            'role': getattr(user, 'role', 'unknown')
        }
    )


@receiver(user_logged_out)
def audit_user_logout(sender, request, user, **kwargs):
    """
    Signal pour logger les déconnexions.
    
    Requirements: 8.2
    """
    from apps.core.models import AuditLog
    
    if user:
        # Extraire l'IP et le User-Agent manuellement
        ip_address = AuditLog.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        AuditLog.log(
            action=AuditLog.Action.LOGOUT,
            user=user,
            model_name='accounts.User',
            object_id=user.pk,
            object_repr=str(user),
            ip_address=ip_address,
            user_agent=user_agent,
            path=request.path,
            extra_data={
                'username': user.username
            }
        )


@receiver(user_login_failed)
def audit_user_login_failed(sender, credentials, request=None, **kwargs):
    """
    Signal pour logger les tentatives de connexion échouées.
    
    Requirements: 8.2
    """
    from apps.core.models import AuditLog
    
    username = credentials.get('username', 'unknown')
    
    if request:
        ip_address = AuditLog.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        AuditLog.log(
            action=AuditLog.Action.LOGIN_FAILED,
            user=None,
            model_name='accounts.User',
            ip_address=ip_address,
            user_agent=user_agent,
            path=request.path,
            extra_data={
                'attempted_username': username
            }
        )
    else:
        AuditLog.log(
            action=AuditLog.Action.LOGIN_FAILED,
            model_name='accounts.User',
            extra_data={
                'attempted_username': username
            }
        )
