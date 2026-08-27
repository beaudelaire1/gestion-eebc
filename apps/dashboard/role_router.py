from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from apps.core.role_helpers import get_user_effective_roles
from . import views


ROLE_HOME_PRIORITY = (
    ('finance', 'finance:dashboard'),
    ('responsable_club', 'bibleclub:home'),
    ('moniteur', 'bibleclub:home'),
    ('chauffeur', 'transport:requests'),
    ('responsable_groupe', 'groups:list'),
    ('secretariat', 'members:list'),
    ('encadrant', 'members:list'),
    ('diacre', 'documents:list'),
)


@login_required
def role_home(request):
    """Point d'entrée interne contextualisé par rôle."""
    effective_roles = get_user_effective_roles(request.user)

    if request.user.is_superuser or 'admin' in effective_roles:
        return views.home(request)

    for role, route_name in ROLE_HOME_PRIORITY:
        if role in effective_roles:
            return redirect(route_name)

    # Les rôles sans module interne explicite restent sur le parcours public.
    return redirect('public:home')
