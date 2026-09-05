"""Rattachement d'une demande de transport au demandeur connecté.

Un compte peut porter une fiche membre, une fiche jeune, ou les deux :
- un membre adulte n'a qu'une fiche ``members.Member`` ;
- un jeune membre de l'église a les deux, reliées par
  ``YoungMember.linked_member`` ;
- un jeune non membre n'a qu'une fiche ``young.YoungMember``.

Le troisième cas est la raison d'être de ce module : rattacher une demande
uniquement à la fiche membre laisserait ces jeunes sans accès à leur propre
demande ni au suivi du chauffeur.
"""
from django.db.models import Q


def member_profile(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    return getattr(user, 'member_profile', None)


def young_profile(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    return getattr(user, 'young_profile', None)


def requester_filter_q(user):
    """Demandes déposées par ``user``, quel que soit le profil qui le décrit."""
    return Q(requester_member__user=user) | Q(requester_young__user=user)


def is_requester(transport_request, user):
    """Whether ``user`` is the person this ride was requested for."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    for profile in (
        transport_request.requester_member,
        transport_request.requester_young,
    ):
        if profile and profile.user_id == user.id:
            return True
    return False


def requester_profile(transport_request):
    """Fiche décrivant le demandeur, fiche membre en premier.

    Les deux modèles exposent ``family``, ``city`` et ``postal_code``, ce qui
    permet de résoudre l'adresse de prise en charge sans distinguer les cas.
    """
    return transport_request.requester_member or transport_request.requester_young
