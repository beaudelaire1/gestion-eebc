"""Compteur de notifications non lues pour la cloche de la barre supérieure.

La cloche renvoyait vers la liste sans jamais dire s'il y avait quelque chose
à lire : il fallait ouvrir la page pour le découvrir. Le modèle porte pourtant
``is_read`` et un index sur ``(user, is_read)``.

Une balise plutôt qu'un processeur de contexte : celui-ci ajouterait la requête
à chaque rendu de gabarit, y compris les emails et les pages d'erreur, alors
que seule la barre supérieure s'en sert.
"""

from django import template

register = template.Library()

# Au-delà, le badge déborde du cercle de la cloche et le nombre exact
# n'apprend plus rien : on sait qu'il y en a beaucoup.
DISPLAY_CAP = 99


@register.simple_tag
def unread_notification_count(user):
    """Nombre de notifications non lues, 0 pour un visiteur anonyme."""
    if not user or not getattr(user, 'is_authenticated', False):
        return 0

    from apps.communication.models import Notification

    return Notification.objects.filter(user=user, is_read=False).count()


@register.filter
def notification_badge(count):
    """Texte du badge : « 99+ » au-delà du plafond d'affichage."""
    try:
        count = int(count)
    except (TypeError, ValueError):
        return ''

    if count <= 0:
        return ''

    return f'{DISPLAY_CAP}+' if count > DISPLAY_CAP else str(count)
