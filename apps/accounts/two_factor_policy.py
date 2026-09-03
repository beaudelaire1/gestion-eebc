"""Qui doit porter un second facteur.

La règle est partagée : le middleware s'en sert pour rediriger, la page de
configuration pour expliquer à l'utilisateur pourquoi il a été redirigé. Les
deux doivent répondre exactement la même chose, sinon la page affiche « facultatif »
à quelqu'un que la plateforme vient de bloquer.
"""

from django.conf import settings

from apps.core.security import PRIVILEGED_USER_ROLES


def enrollment_is_enforced():
    """Interrupteur de déploiement.

    Le désactiver permet d'étaler la mise en place au lieu de bloquer tous les
    responsables dès la mise en production.
    """
    return bool(
        getattr(settings, 'TWO_FACTOR_ENFORCED_FOR_PRIVILEGED_ROLES', True)
    )


def requires_2fa_enrollment(user):
    """Les comptes privilégiés doivent enrôler ; les membres restent libres.

    Ce sont les comptes qui accèdent aux fiches membres, aux finances et aux
    dossiers pastoraux : un mot de passe volé ne doit pas suffire. Imposer une
    application d'authentification à toute l'assemblée exclurait en revanche
    chaque personne sans smartphone.
    """
    if not user.is_authenticated:
        return False

    if not enrollment_is_enforced():
        return False

    if getattr(user, 'two_factor_enabled', False):
        return False

    # Le staff et les superutilisateurs atteignent l'admin Django quel que soit
    # le rôle CSV.
    if user.is_superuser or user.is_staff:
        return True

    return bool(set(user.get_roles_list()) & PRIVILEGED_USER_ROLES)
