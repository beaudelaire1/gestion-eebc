"""Identité de l'organisme disponible dans n'importe quel template.

Les documents PDF sont rendus par des vues et des services différents, dont
plusieurs ne construisent pas de contexte contenant l'église. Passer par des
balises évite d'avoir à modifier chaque appelant — et surtout d'en oublier un.
"""

from django import template

from apps.core.church import CHURCH_INFO, church_contact_line

register = template.Library()


@register.simple_tag
def church_name():
    return CHURCH_INFO['name']


@register.simple_tag
def church_address():
    return CHURCH_INFO['address']


@register.simple_tag
def church_contact(separator=' — '):
    """Téléphone et email, sans séparateur orphelin si l'un manque."""
    return church_contact_line(separator)
