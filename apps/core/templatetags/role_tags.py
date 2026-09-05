"""Test des rôles dans les gabarits.

``User.role`` stocke plusieurs rôles séparés par des virgules. Les gabarits
écrivaient ``{% if user.role == 'admin' %}``, une égalité qui n'est vraie que
pour un compte n'ayant qu'un seul rôle : un compte ``admin,finance`` voyait
disparaître les boutons réservés aux administrateurs, dont la création d'un
département. Ce filtre passe par ``has_any_role`` du modèle, qui découpe la
chaîne comme il faut.
"""

from django import template

from apps.core.security import (
    PRIVILEGED_USER_ROLES,
    can_view_sensitive_member_data,
    user_has_any_role,
)

register = template.Library()


@register.filter
def has_any_role(user, roles):
    """Vrai si l'utilisateur porte au moins un des rôles demandés.

    Usage : ``{% if user|has_any_role:"admin,secretariat" %}``
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    # Cohérent avec user_has_any_role dans apps.core.security : un
    # superutilisateur passe tous les contrôles de rôle.
    if getattr(user, 'is_superuser', False):
        return True

    wanted = {role.strip() for role in str(roles).split(',') if role.strip()}
    if not wanted:
        return False

    get_roles = getattr(user, 'get_roles_list', None)
    if not callable(get_roles):
        return False

    return bool(wanted & set(get_roles()))


@register.filter
def has_management_role(user):
    """Vrai si le compte possède au moins un rôle de gestion EEBC."""
    return user_has_any_role(user, *PRIVILEGED_USER_ROLES)


@register.filter
def can_view_contact_details(user):
    """Vrai si le compte peut voir les coordonnées personnelles d'un membre.

    Les listes de groupe et de département sont lisibles par toute
    l'assemblée ; le téléphone et l'e-mail d'une personne, non.
    """
    return can_view_sensitive_member_data(user)
