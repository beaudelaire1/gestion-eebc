"""Sélections partagées sur les annonces.

La définition d'une annonce « active » — publiée, dans sa fenêtre de dates —
était réécrite à chaque endroit qui en avait besoin. La centraliser évite que
le portail interne et le site public divergent.
"""

from django.db.models import Q
from django.utils import timezone

from apps.core.security import is_ordinary_member

from .models import Announcement


def get_active_announcements(now=None):
    """Annonces publiées et dans leur fenêtre de publication."""
    now = now or timezone.now()

    return (
        Announcement.objects.filter(is_active=True)
        .filter(Q(start_date__isnull=True) | Q(start_date__lte=now))
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=now))
        .order_by('-is_pinned', '-created_at')
    )


def get_public_announcements(now=None):
    """Annonces destinées au site vitrine.

    La visibilité `PUBLIC` existait dans le modèle sans qu'aucune page publique
    ne consomme les annonces : la cocher ne publiait rien. Seules les annonces
    explicitement publiques sortent du portail interne.
    """

    return get_active_announcements(now).filter(
        visibility=Announcement.Visibility.PUBLIC
    )


def get_announcements_for_user(user, now=None):
    """Apply announcement visibility for an authenticated portal user."""
    announcements = get_active_announcements(now)
    if is_ordinary_member(user):
        return announcements.filter(
            visibility__in=(
                Announcement.Visibility.PUBLIC,
                Announcement.Visibility.MEMBERS,
            )
        )
    return announcements
