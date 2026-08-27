"""
Module de permissions RBAC (Role-Based Access Control) pour Gestion EEBC.

Ce module fournit:
- Un décorateur @role_required pour les vues fonctionnelles
- Un décorateur @module_required pour les modules internes
- Un mixin RoleRequiredMixin pour les vues basées sur classes
- Des fonctions utilitaires pour vérifier les rôles et l'accès aux modules
- Logging des tentatives d'accès refusées (Requirement 8.4)
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect


def log_access_denied(request, required_roles, view_name=''):
    """Logger une tentative d'accès refusée."""
    from apps.core.models import AuditLog

    user_role = getattr(request.user, 'role', 'unknown') if request.user.is_authenticated else 'anonymous'

    AuditLog.log_from_request(
        request=request,
        action=AuditLog.Action.ACCESS_DENIED,
        extra_data={
            'required_roles': list(required_roles),
            'user_role': user_role,
            'view_name': view_name,
            'method': request.method,
        },
    )


# =============================================================================
# CONFIGURATION DES RÔLES ET PERMISSIONS
# =============================================================================

ROLE_PERMISSIONS = {
    'admin': {
        'modules': ['*'],
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
    'chauffeur': {
        'modules': ['transport'],
        'actions': ['view', 'update'],
        'scope': 'driver_workqueue',
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

def _assigned_roles(user):
    """Retourne les rôles explicitement affectés à l'utilisateur."""
    if not user or not user.is_authenticated:
        return []
    if hasattr(user, 'get_roles_list'):
        return user.get_roles_list()
    role = getattr(user, 'role', '') or ''
    return [item.strip() for item in role.split(',') if item.strip()]


def _effective_roles(user):
    """Retourne les rôles effectifs en tenant compte de la hiérarchie du projet."""
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return {'admin'}

    try:
        from apps.core.role_helpers import get_user_effective_roles
        return set(get_user_effective_roles(user))
    except Exception:
        # Le contrôle d'accès ne doit pas échouer si le helper hiérarchique
        # est indisponible pendant une migration ou un chargement partiel.
        return set(_assigned_roles(user))


def has_role(user, *roles):
    """
    Vérifie si l'utilisateur possède au moins un rôle demandé.

    Cette fonction conserve la sémantique historique: elle vérifie les rôles
    explicitement affectés. La hiérarchie est utilisée par l'accès aux modules,
    où elle est nécessaire pour les rôles pastoraux de develop.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    user_roles = _assigned_roles(user)
    if 'admin' in user_roles:
        return True
    return any(role in user_roles for role in roles)


def get_user_permissions(user):
    """Retourne l'union des permissions des rôles effectifs de l'utilisateur."""
    if not user or not user.is_authenticated:
        return {'modules': [], 'actions': [], 'scopes': []}
    if user.is_superuser:
        return {'modules': ['*'], 'actions': ['*'], 'scopes': []}

    modules = set()
    actions = set()
    scopes = set()

    for role in _effective_roles(user):
        permission = ROLE_PERMISSIONS.get(role)
        if not permission:
            continue
        modules.update(permission.get('modules', []))
        actions.update(permission.get('actions', []))
        if permission.get('scope'):
            scopes.add(permission['scope'])

    if '*' in modules or '*' in actions:
        return {'modules': ['*'], 'actions': ['*'], 'scopes': sorted(scopes)}

    return {
        'modules': sorted(modules),
        'actions': sorted(actions),
        'scopes': sorted(scopes),
    }


def can_access_module(user, module, *, internal=True):
    """
    Vérifie si l'utilisateur peut accéder à un module de gestion.

    Le rôle membre conserve ses permissions de lecture pour les parcours
    publics, mais le scope ``public_only`` ne lui ouvre aucun module interne.
    Pour les utilisateurs multi-rôles, un autre rôle effectif peut toutefois
    accorder explicitement l'accès au module.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    effective_roles = _effective_roles(user)
    if 'admin' in effective_roles:
        return True

    for role in effective_roles:
        permission = ROLE_PERMISSIONS.get(role)
        if not permission:
            continue
        if internal and permission.get('scope') == 'public_only':
            continue
        modules = permission.get('modules', [])
        if '*' in modules or module in modules:
            return True

    return False


# =============================================================================
# DÉCORATEURS D'ACCÈS
# =============================================================================

def role_required(*roles, redirect_url='dashboard:home', message=None):
    """Décorateur pour restreindre une vue fonctionnelle aux rôles indiqués."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if has_role(request.user, *roles):
                return view_func(request, *args, **kwargs)

            log_access_denied(request, roles, view_func.__name__)
            error_message = message or "Vous n'avez pas les permissions nécessaires pour accéder à cette page."
            messages.error(request, error_message)
            return redirect(redirect_url)

        return _wrapped_view

    return decorator


def module_required(module, redirect_url='dashboard:home', message=None):
    """Décorateur pour restreindre une vue à un module interne autorisé."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if can_access_module(request.user, module, internal=True):
                return view_func(request, *args, **kwargs)

            log_access_denied(request, (f'module:{module}',), view_func.__name__)
            error_message = message or "Vous n'avez pas les permissions nécessaires pour accéder à cette page."
            messages.error(request, error_message)
            return redirect(redirect_url)

        return _wrapped_view

    return decorator


# =============================================================================
# MIXIN RoleRequiredMixin POUR LES CBV
# =============================================================================

class RoleRequiredMixin(AccessMixin):
    """Mixin qui restreint une vue basée sur classe aux rôles configurés."""

    allowed_roles = ()
    permission_denied_message = "Vous n'avez pas les permissions nécessaires pour accéder à cette page."
    permission_denied_redirect = 'dashboard:home'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.has_permission():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_role(self.request.user, *self.allowed_roles)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            log_access_denied(
                self.request,
                self.allowed_roles,
                self.__class__.__name__,
            )
            messages.error(self.request, self.permission_denied_message)
            return redirect(self.permission_denied_redirect)
        return super().handle_no_permission()
