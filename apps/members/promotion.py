"""Création de la fiche membre d'un jeune ou d'un enfant du club biblique.

Les fiches jeunesse et club biblique vivent à côté de l'annuaire. Tant
qu'aucune fiche ``Member`` ne leur correspond, la personne reste invisible
là où l'application ne connaît que ``Member`` : liste des membres,
rattachement à une famille, sélecteurs de groupe ou de département.

L'import Excel des jeunes fait le même rattachement dans
``apps.imports.young_links``, avec des messages d'erreur qui renvoient aux
colonnes du fichier. Ce module est son équivalent pour la saisie courante.
"""
from django.core.exceptions import ValidationError

from .models import Member


# Champs repris tels quels quand la fiche membre est créée. Une fiche jeune
# et une fiche enfant ne portent pas les mêmes : les absents sont ignorés.
COPIED_FIELDS = (
    'first_name',
    'last_name',
    'date_of_birth',
    'gender',
    'email',
    'phone',
    'address',
    'city',
    'postal_code',
    'site',
    'is_baptized',
    'baptism_date',
)


def find_matching_member(profile):
    """Fiche membre décrivant déjà cette personne, sinon ``None``.

    L'homonymie est résolue par la date de naissance. Toute ambiguïté est
    refusée plutôt qu'arbitrée : fusionner deux personnes distinctes coûte
    plus cher que de demander une vérification.
    """
    candidates = Member.objects.filter(
        first_name__iexact=profile.first_name,
        last_name__iexact=profile.last_name,
    )
    matches = list(candidates.filter(date_of_birth=profile.date_of_birth)[:2])
    if len(matches) > 1:
        raise ValidationError(
            "Plusieurs fiches membres portent ce nom et cette date de naissance : "
            "reliez la bonne fiche à la main."
        )
    if matches:
        return matches[0]
    if candidates.filter(date_of_birth__isnull=True).exists():
        raise ValidationError(
            "Une fiche membre homonyme n'a pas de date de naissance : "
            "vérifiez s'il s'agit de la même personne avant de la relier."
        )
    email = (getattr(profile, 'email', '') or '').strip()
    if email and Member.objects.filter(email__iexact=email).exists():
        raise ValidationError(
            "Cet email appartient déjà à une fiche membre : "
            "vérifiez son identité avant de la relier."
        )
    return None


def link_or_create_member(profile):
    """Relier ``profile`` à sa fiche membre, en la créant si besoin.

    Retourne ``(member, created)``. L'appelant enregistre ``profile``.
    """
    if profile.linked_member_id:
        return profile.linked_member, False

    member = find_matching_member(profile)
    created = member is None
    if created:
        values = {
            field: getattr(profile, field)
            for field in COPIED_FIELDS
            if hasattr(profile, field)
        }
        values['status'] = Member.Status.ACTIF
        member = Member.objects.create(**values)

    profile.linked_member = member
    return member, created
