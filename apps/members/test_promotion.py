"""Passage d'une fiche jeunesse ou club biblique à l'annuaire des membres."""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.bibleclub.models import Child
from apps.members.models import Member
from apps.members.promotion import link_or_create_member, link_or_create_profile
from apps.young.models import YoungMember


pytestmark = pytest.mark.django_db


@pytest.fixture
def secretariat_client(client):
    user = get_user_model().objects.create_user(
        username='secretariat',
        email='secretariat@example.test',
        password='Secret-pass-123!',
        role='secretariat',
    )
    client.force_login(user)
    return client


@pytest.fixture
def young():
    return YoungMember.objects.create(
        first_name='Naomi',
        last_name='Kaline',
        date_of_birth=date(2008, 4, 17),
        gender=YoungMember.Gender.FEMININ,
        phone='0694445566',
        city='Cayenne',
    )


def test_promotion_creates_the_church_record(young):
    member, created = link_or_create_member(young)
    young.save(update_fields=['linked_member'])

    assert created is True
    assert member.first_name == 'Naomi'
    assert member.date_of_birth == young.date_of_birth
    assert member.status == Member.Status.ACTIF
    assert young.linked_member == member


def test_promotion_reuses_an_existing_church_record(young):
    existing = Member.objects.create(
        first_name='naomi',
        last_name='KALINE',
        date_of_birth=young.date_of_birth,
    )

    member, created = link_or_create_member(young)

    assert created is False
    assert member == existing


def test_promotion_refuses_to_arbitrate_between_homonyms(young):
    for _ in range(2):
        Member.objects.create(
            first_name='Naomi',
            last_name='Kaline',
            date_of_birth=young.date_of_birth,
        )

    with pytest.raises(ValidationError):
        link_or_create_member(young)


def test_promotion_flags_a_homonym_without_a_birth_date(young):
    Member.objects.create(first_name='Naomi', last_name='Kaline')

    with pytest.raises(ValidationError):
        link_or_create_member(young)


def test_promoted_young_shows_up_in_the_member_directory(secretariat_client, young):
    response = secretariat_client.post(
        reverse('young:member_link_church_record', args=[young.pk])
    )
    young.refresh_from_db()

    directory = secretariat_client.get(reverse('members:list'))

    assert response.status_code == 302
    assert young.linked_member is not None
    assert young.full_name in directory.content.decode()


def test_promoted_child_shows_up_in_the_group_member_choices(secretariat_client):
    child = Child.objects.create(
        first_name='Élie',
        last_name='Mombo',
        date_of_birth=date(2015, 2, 3),
        gender='M',
    )

    response = secretariat_client.post(
        reverse('bibleclub:child_link_church_record', args=[child.pk])
    )
    child.refresh_from_db()

    from apps.groups.forms import GroupMembersForm

    choices = GroupMembersForm().fields['members'].queryset

    assert response.status_code == 302
    assert child.linked_member in choices


def test_promotion_is_idempotent(secretariat_client, young):
    for _ in range(2):
        secretariat_client.post(
            reverse('young:member_link_church_record', args=[young.pk])
        )

    assert Member.objects.filter(last_name='Kaline').count() == 1


# ---------------------------------------------------------------------------
# Sens inverse : de l'annuaire vers la jeunesse ou le club biblique
# ---------------------------------------------------------------------------


@pytest.fixture
def adult_member():
    return Member.objects.create(
        first_name='Ruth',
        last_name='Anselme',
        date_of_birth=date(2009, 11, 2),
        gender='F',
        phone='0694778899',
        city='Rémire',
    )


def test_member_can_be_registered_in_the_youth_ministry(adult_member):
    young, created = link_or_create_profile(adult_member, YoungMember)

    assert created is True
    assert young.linked_member == adult_member
    assert young.first_name == 'Ruth'
    assert young.date_of_birth == adult_member.date_of_birth


def test_member_registration_in_youth_is_idempotent(adult_member):
    first, _ = link_or_create_profile(adult_member, YoungMember)
    second, created = link_or_create_profile(adult_member, YoungMember)

    assert created is False
    assert first == second
    assert YoungMember.objects.count() == 1


def test_member_without_civil_status_cannot_be_registered():
    """Une fiche jeune exige une date de naissance et un genre."""
    incomplete = Member.objects.create(first_name='Sans', last_name='Etatcivil')

    with pytest.raises(ValidationError):
        link_or_create_profile(incomplete, YoungMember)


def test_member_detail_offers_both_registrations(secretariat_client, adult_member):
    body = secretariat_client.get(
        reverse('members:detail', args=[adult_member.pk])
    ).content.decode()

    assert reverse('members:link_youth_record', args=[adult_member.pk]) in body
    assert reverse('members:link_bibleclub_record', args=[adult_member.pk]) in body


def test_registering_a_member_in_the_bible_club_from_their_record(
    secretariat_client, adult_member
):
    response = secretariat_client.post(
        reverse('members:link_bibleclub_record', args=[adult_member.pk])
    )

    child = Child.objects.get()
    assert response.status_code == 302
    assert child.linked_member == adult_member
    assert child.first_name == 'Ruth'


def test_round_trip_keeps_a_single_pair_of_records(secretariat_client, young):
    """Aller de la jeunesse vers l'annuaire puis revenir ne duplique rien."""
    secretariat_client.post(
        reverse('young:member_link_church_record', args=[young.pk])
    )
    young.refresh_from_db()

    secretariat_client.post(
        reverse('members:link_youth_record', args=[young.linked_member.pk])
    )

    assert YoungMember.objects.count() == 1
    assert Member.objects.filter(last_name='Kaline').count() == 1
