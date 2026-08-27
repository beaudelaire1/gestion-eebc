from django import template

from apps.core.permissions import can_access_module


register = template.Library()


@register.simple_tag
def module_access(user, module):
    """Retourne True si l'utilisateur peut voir un module interne."""
    return can_access_module(user, module, internal=True)
