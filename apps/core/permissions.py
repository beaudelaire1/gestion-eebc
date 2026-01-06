"""
Module de permissions RBAC (Role-Based Access Control) pour Gestion EEBC.

Ce module fournit:
- Un décorateur @role_required pour les vues fonctionnelles
- Un mixin RoleRequiredMixin pour les vues basées sur classes
- Des fonctions utilitaires pour vérifier les rôles
- Logging des tentatives d'accès refusées (Requirement 8.4)
"""

from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.http import HttpResponseForbidden


def log_access_denied(request, required_roles, view_name=''):
    """
    Logger une tentative d'accès refusée.
    
    Args:
        request: La requête HTTP
        required_roles: Les rôles requis pour accéder à la vue
        view_name: Nom de la vue (optionnel)
    
    Requirements: 8.4
    """
    from apps.core.models import AuditLog
    
    user_role = getattr(request.user, 'role', 'unknown') if request.user.is_authenticated else 'anonymous'
    
    AuditLog.log_from_request(
        request=request,
        action=AuditLog.Action.ACCESS_DENIED,
        extra_data={
            'required_roles': list(required_roles),
            'user_role': user_role,
            'view_name': view_name,
            'method': request.method
        }
    )


# =============================================================================
# CONFIGURATION DES RÔLES ET PERMISSIONS
# =============================================================================

ROLE_PERMISSIONS = {
    'admin': {
        'modules': ['*'],  # Accès total
        'actions': ['*'],
    },
    'secretariat': {
        'modules': ['members', 'accounts', 'events', 'groups'],
        'actions': ['view', 'create', 'update', 'export'],
    },
    'finance': {
        'modules': ['finance', 'campaigns'],
        'actions': ['view', 'create', 'update', 'export', 'validate'],
    },
    'responsable_club': {
        'modules': ['bibleclub'],
        'actions': ['view', 'create', 'update', 'export'],
    },
    'moniteur': {
        'modules': ['bibleclub'],
        'actions': ['view', 'update'],
        'scope': 'own_class',
    },
    'responsable_groupe': {
        'modules': ['groups', 'worship'],
        'actions': ['view', 'update'],
        'scope': 'own_group',
    },
    'encadrant': {
        'modules': ['members'],
        'actions': ['view'],
        'scope': 'pastoral_data',
    },
    'membre': {
        'modules': ['members', 'events'],
        'actions': ['view'],
        'scope': 'public_only',
    },
}


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def has_role(user, *roles):
    """
    Vérifie si l'utilisateur a l'un des rôles spécifiés.
    
    Args:
        user: L'utilisateur à vérifier
        *roles: Liste des rôles autorisés
    
    Returns:
        bool: True si l'utilisateur a l'un des rôles, False sinon
    
    Notes:
        - Les superusers ont toujours accès (retourne True)
        - Les utilisateurs avec le rôle 'admin' ont toujours accès
        - Un utilisateur non authentifié retourne False
    
    Usage:
        if has_role(request.user, 'admin', 'finance'):
            # L'utilisateur a accès
    """
    # Vérifier que l'utilisateur est authentifié
    if not user or not user.is_authenticated:
        return False
    
    # Les superusers ont toujours accès
    if user.is_superuser:
        return True
    
    # Vérifier si l'utilisateur a le rôle admin (accès total)
    if hasattr(user, 'role') and user.role == 'admin':
        return True
    
    # Vérifier si l'utilisateur a l'un des rôles spécifiés
    if hasattr(user, 'role') and user.role in roles:
        return True
    
    return False


def get_user_permissions(user):
    """
    Retourne les permissions de l'utilisateur basées sur son rôle.
    
    Args:
        user: L'utilisateur dont on veut les permissions
    
    Returns:
        dict: Dictionnaire des permissions avec 'modules' et 'actions'
    """
    if not user or not user.is_authenticated:
        return {'modules': [], 'actions': []}
    
    if user.is_superuser:
        return {'modules': ['*'], 'actions': ['*']}
    
    role = getattr(user, 'role', 'membre')
    return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS['membre'])


# =============================================================================
# DÉCORATEUR @role_required
# =============================================================================

def role_required(*roles, redirect_url='dashboard:home', message=None):
    """
    Décorateur pour restreindre l'accès aux vues par rôle.
    
    Ce décorateur vérifie que l'utilisateur connecté possède l'un des rôles
    spécifiés. Si ce n'est pas le cas, il est redirigé avec un message d'erreur.
    Les tentatives d'accès refusées sont loggées (Requirement 8.4).
    
    Args:
        *roles: Liste des rôles autorisés (ex: 'admin', 'finance')
        redirect_url: URL de redirection si accès refusé (défaut: 'dashboard:home')
        message: Message d'erreur personnalisé (optionnel)
    
    Returns:
        function: Le décorateur configuré
    
    Usage:
        @login_required
        @role_required('admin', 'finance')
        def my_view(request):
            ...
        
        @login_required
        @role_required('admin', redirect_url='accounts:login', message="Accès réservé aux admins")
        def admin_only_view(request):
            ...
    
    Notes:
        - Ce décorateur doit être utilisé APRÈS @login_required
        - Les superusers et admins ont toujours accès
        - Un message d'erreur est affiché via le système de messages Django
        - Les tentatives d'accès refusées sont loggées dans AuditLog
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Vérifier si l'utilisateur a l'un des rôles requis
            if has_role(request.user, *roles):
                return view_func(request, *args, **kwargs)
            
            # Accès refusé - logger la tentative (Requirement 8.4)
            log_access_denied(request, roles, view_func.__name__)
            
            # Préparer le message d'erreur
            error_message = message or "Vous n'avez pas les permissions nécessaires pour accéder à cette page."
            messages.error(request, error_message)
            
            # Rediriger vers l'URL spécifiée
            return redirect(redirect_url)
        
        return _wrapped_view
    return decorator


# =============================================================================
# MIXIN RoleRequiredMixin POUR LES CBV
# =============================================================================

class RoleRequiredMixin(AccessMixin):
    """
    Mixin pour les vues basées sur classes (CBV) qui restreint l'accès par rôle.
    
    Ce mixin vérifie que l'utilisateur connecté possède l'un des rôles
    définis dans `allowed_roles`. Si ce n'est pas le cas, il est redirigé
    avec un message d'erreur. Les tentatives d'accès refusées sont loggées.
    
    Attributes:
        allowed_roles (tuple): Tuple des rôles autorisés
        permission_denied_message (str): Message d'erreur personnalisé
        permission_denied_redirect (str): URL de redirection si accès refusé
    
    Usage:
        class MyView(RoleRequiredMixin, TemplateView):
            allowed_roles = ('admin', 'finance')
            template_name = 'my_template.html'
        
        class AdminOnlyView(RoleRequiredMixin, ListView):
            allowed_roles = ('admin',)
            permission_denied_message = "Réservé aux administrateurs"
            permission_denied_redirect = 'dashboard:home'
    
    Notes:
        - Ce mixin doit être placé AVANT les autres mixins/vues dans l'héritage
        - Les superusers et admins ont toujours accès
        - Nécessite que l'utilisateur soit authentifié (utiliser LoginRequiredMixin si besoin)
        - Les tentatives d'accès refusées sont loggées dans AuditLog (Requirement 8.4)
    """
    allowed_roles = ()
    permission_denied_message = "Vous n'avez pas les permissions nécessaires pour accéder à cette page."
    permission_denied_redirect = 'dashboard:home'
    
    def dispatch(self, request, *args, **kwargs):
        """
        Vérifie les permissions avant de traiter la requête.
        """
        # Vérifier que l'utilisateur est authentifié
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Vérifier si l'utilisateur a l'un des rôles requis
        if not self.has_permission():
            return self.handle_no_permission()
        
        return super().dispatch(request, *args, **kwargs)
    
    def has_permission(self):
        """
        Vérifie si l'utilisateur a les permissions requises.
        
        Returns:
            bool: True si l'utilisateur a l'un des rôles autorisés
        """
        return has_role(self.request.user, *self.allowed_roles)
    
    def handle_no_permission(self):
        """
        Gère le cas où l'utilisateur n'a pas les permissions requises.
        
        Affiche un message d'erreur, logge la tentative et redirige vers l'URL configurée.
        """
        if self.request.user.is_authenticated:
            # Logger la tentative d'accès refusée (Requirement 8.4)
            log_access_denied(
                self.request, 
                self.allowed_roles, 
                self.__class__.__name__
            )
            
            messages.error(self.request, self.permission_denied_message)
            return redirect(self.permission_denied_redirect)
        
        # Si non authentifié, utiliser le comportement par défaut (redirection login)
        return super().handle_no_permission()
