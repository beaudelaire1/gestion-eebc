"""Passage entre l'annuaire des membres et les fiches jeunesse / club biblique.

Les fiches jeunesse et club biblique vivent à côté de l'annuaire. Tant
qu'aucune fiche ``Member`` ne leur correspond, la personne reste invisible
là où l'application ne connaît que ``Member`` : liste des membres,
rattachement à une famille, sélecteurs de groupe ou de département.

Le rattachement va dans les deux sens : un jeune peut entrer dans l'annuaire,
et un membre déjà inscrit peut recevoir sa fiche jeunesse ou club biblique.

L'import Excel des jeunes fait le même rattachement dans
``apps.imports.young_links``, avec des messages d'erreur qui renvoient aux
colonnes du fichier. Ce module est son équivalent pour la saisie courante.
"""
import posixpath

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

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


def copy_photo(source, target):
    """Recopier la photo de ``source`` dans le dossier du modèle ``target``.

    Le champ ne peut pas être repris tel quel : deux fiches partageraient
    alors le même fichier, rangé dans le dossier du modèle d'origine.

    Une photo introuvable dans le stockage n'interrompt rien : elle est un
    confort, et refuser le rattachement pour autant coûterait plus que de
    laisser la fiche sans portrait.
    """
    photo = getattr(source, 'photo', None)
    if not photo or getattr(target, 'photo', None):
        return False

    try:
        photo.open('rb')
        content = ContentFile(photo.read())
    except Exception:
        return False
    finally:
        try:
            photo.close()
        except Exception:
            pass

    target.photo.save(posixpath.basename(photo.name), content, save=False)
    return True


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
        member = profile.linked_member
        if copy_photo(profile, member):
            member.save(update_fields=['photo'])
        return member, False

    member = find_matching_member(profile)
    created = member is None
    if created:
        values = {
            field: getattr(profile, field)
            for field in COPIED_FIELDS
            if hasattr(profile, field)
        }
        values['status'] = Member.Status.ACTIF
        member = Member(**values)
        copy_photo(profile, member)
        member.save()
    elif copy_photo(profile, member):
        member.save(update_fields=['photo'])

    profile.linked_member = member
    return member, created


def link_or_create_profile(member, model):
    """Créer la fiche jeunesse ou club biblique d'un membre, et la relier.

    Réciproque de :func:`link_or_create_member`. Retourne ``(profile,
    created)``. Une fiche jeune ou enfant exige une date de naissance et un
    genre : sans eux, la fiche serait invalide, et deviner l'un ou l'autre
    reviendrait à inventer une donnée d'état civil.
    """
    existing = model.objects.filter(linked_member=member).first()
    if existing is not None:
        if copy_photo(member, existing):
            existing.save(update_fields=['photo'])
        return existing, False

    missing = [
        label
        for field, label in (('date_of_birth', 'date de naissance'), ('gender', 'genre'))
        if not getattr(member, field, None)
    ]
    if missing:
        raise ValidationError(
            "Complétez d'abord la fiche membre : " + " et ".join(missing) + "."
        )

    target_fields = {
        field.name
        for field in model._meta.get_fields()
        if getattr(field, 'concrete', False)
    }
    values = {
        name: getattr(member, name)
        for name in COPIED_FIELDS
        if name in target_fields and hasattr(member, name)
    }
    values['linked_member'] = member
    profile = model(**values)
    copy_photo(member, profile)
    profile.save()
    return profile, True
