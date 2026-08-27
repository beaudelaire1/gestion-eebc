from django import template

from apps.core.permissions import can_access_module, has_role


register = template.Library()


@register.simple_tag
def module_access(user, module):
    """Retourne True si l'utilisateur peut voir un module interne."""
    return can_access_module(user, module, internal=True)


@register.simple_tag
def role_access(user, *roles):
    """Retourne True si l'utilisateur possède au moins un des rôles fournis."""
    return has_role(user, *roles)
