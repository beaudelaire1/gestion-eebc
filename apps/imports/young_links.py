"""Rattachements explicites d'une ligne jeunesse, dans la transaction d'import."""

import pandas as pd
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.accounts.services import AccountsService
from apps.core.models import AuditLog
from apps.members.models import Member
from apps.young.models import YoungMember


def text_value(row, column):
    value = row.get(column)
    return "" if pd.isna(value) else str(value).strip()


def optional_boolean(row, column):
    value = text_value(row, column).lower()
    if not value:
        return None
    if value not in ("oui", "non"):
        raise ValidationError(f"{column} : utilisez oui, non ou une cellule vide.")
    return value == "oui"


def same_identity(member, young):
    return (
        member.first_name.strip().casefold() == young.first_name.strip().casefold()
        and member.last_name.strip().casefold() == young.last_name.strip().casefold()
        and member.date_of_birth in (None, young.date_of_birth)
    )


def resolve_member(young, row):
    belongs = optional_boolean(row, "membre_eglise")
    member_id = text_value(row, "membre_id")
    current = young.linked_member
    if belongs is False and (member_id or current):
        raise ValidationError(
            "membre_eglise=non contredit la fiche membre liée ; vérifier le rattachement."
        )
    if member_id:
        if belongs is not True:
            raise ValidationError("Indiquez membre_eglise=oui pour utiliser membre_id.")
        member = Member.objects.select_for_update().filter(member_id=member_id).first()
        if member is None or not same_identity(member, young):
            raise ValidationError(
                "membre_id introuvable ou identité différente de celle du jeune."
            )
        if current and current.pk != member.pk:
            raise ValidationError("Le jeune est déjà lié à une autre fiche membre.")
        return member
    if belongs is not True:
        return current
    if current:
        if not same_identity(current, young):
            raise ValidationError(
                "L'identité de la fiche membre liée doit être vérifiée."
            )
        return current
    return find_or_create_member(young)


def find_or_create_member(young):
    candidates = Member.objects.select_for_update().filter(
        first_name__iexact=young.first_name,
        last_name__iexact=young.last_name,
    )
    matches = list(candidates.filter(date_of_birth=young.date_of_birth)[:2])
    if len(matches) > 1:
        raise ValidationError("Plusieurs membres correspondent ; renseignez membre_id.")
    if matches:
        return matches[0]
    if candidates.filter(date_of_birth__isnull=True).exists():
        raise ValidationError(
            "Membre homonyme sans date de naissance ; renseignez membre_id après vérification."
        )
    if young.email and Member.objects.filter(email__iexact=young.email).exists():
        raise ValidationError(
            "Cet email appartient déjà à une fiche membre ; vérifier son identité et membre_id."
        )
    fields = (
        "first_name",
        "last_name",
        "date_of_birth",
        "gender",
        "email",
        "phone",
        "address",
        "city",
        "postal_code",
        "is_baptized",
        "baptism_date",
        "site",
    )
    return Member.objects.create(**{field: getattr(young, field) for field in fields})


def resolve_user(young, member, create_account, actor):
    linked_user = member.user if member else None
    if young.user_id and linked_user and young.user_id != linked_user.pk:
        raise ValidationError(
            "Le jeune et le membre sont liés à des comptes différents."
        )
    user = young.user or linked_user
    if user or not create_account:
        return user
    from .services import validate_email

    email = validate_email(young.email)
    # Un email seul, même accompagné d'un nom, n'autorise pas à reprendre un compte.
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError(
            "Un compte utilise déjà cet email ; rattachez-le manuellement après vérification."
        )
    result = AccountsService.create_user_by_team(
        first_name=young.first_name,
        last_name=young.last_name,
        email=email,
        roles=[User.Role.MEMBRE],
        created_by=actor,
        phone=young.phone,
        send_email=False,
    )
    if not result.success:
        raise ValidationError("Impossible de créer le compte utilisateur.")
    return result.data["user"]


def apply_young_links(young, row, actor):
    if (
        not actor
        or not actor.is_active
        or not (actor.is_superuser or actor.has_any_role("admin", "secretariat"))
    ):
        raise ValidationError(
            "Seuls les administrateurs et le secrétariat peuvent importer les jeunes."
        )
    create_account = optional_boolean(row, "creer_compte")
    member = resolve_member(young, row)
    if (
        member
        and YoungMember.objects.filter(linked_member=member)
        .exclude(pk=young.pk)
        .exists()
    ):
        raise ValidationError("Cette fiche membre est déjà liée à un autre jeune.")
    user = resolve_user(young, member, create_account, actor)
    validate_user_links(young, member, user)
    changes = {}
    for field, obj in (("linked_member", member), ("user", user)):
        new_id = obj.pk if obj else None
        old_id = getattr(young, f"{field}_id")
        if old_id != new_id:
            changes[field] = {"old": old_id, "new": new_id}
            setattr(young, field, obj)
    if member and user and not member.user_id:
        member.user = user
        member.save(update_fields=["user"])
    if changes:
        young.save(update_fields=list(changes))
        AuditLog.objects.create(
            user=actor,
            action=AuditLog.Action.UPDATE,
            model_name="young.YoungMember",
            object_id=young.pk,
            object_repr=str(young),
            changes=changes,
        )
    return changes


def validate_user_links(young, member, user):
    if user:
        if YoungMember.objects.filter(user=user).exclude(pk=young.pk).exists():
            raise ValidationError("Ce compte est déjà lié à un autre jeune.")
        other_members = Member.objects.filter(user=user)
        if member:
            other_members = other_members.exclude(pk=member.pk)
        if other_members.exists():
            raise ValidationError(
                "Ce compte est lié à une autre fiche membre ; vérifier le rattachement."
            )
