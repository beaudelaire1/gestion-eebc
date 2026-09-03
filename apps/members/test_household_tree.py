"""Tests de l'arbre du foyer affiché sur la fiche famille."""

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.core.models import Family
from apps.members.family_views import _build_household_tree
from apps.members.models import Member

pytestmark = pytest.mark.django_db


def _member(family, first, role):
    return Member.objects.create(
        first_name=first, last_name='FOYER', family=family,
        family_role=role, status='actif',
    )


def test_tree_places_each_role_in_its_generation():
    family = Family.objects.create(name='Complet')
    _member(family, 'Pierre', 'PARENT')
    _member(family, 'Jean', 'HEAD')
    _member(family, 'Marie', 'SPOUSE')
    _member(family, 'Luc', 'CHILD')
    _member(family, 'Anna', 'CHILD')
    _member(family, 'Tante', 'OTHER')

    tree = _build_household_tree(family.members.all())

    assert [m.first_name for m in tree['parents']] == ['Pierre']
    assert {m.first_name for m in tree['couple']} == {'Jean', 'Marie'}
    assert {m.first_name for m in tree['children']} == {'Luc', 'Anna'}
    assert [m.first_name for m in tree['others']] == ['Tante']
    assert tree['has_any'] is True


def test_tree_anchors_on_a_member_when_no_head_is_designated():
    """Sans ancrage, un foyer n'afficherait que des enfants suspendus."""
    family = Family.objects.create(name='Sans chef')
    _member(family, 'Adulte', 'OTHER')
    _member(family, 'Enfant', 'CHILD')

    tree = _build_household_tree(family.members.all())

    assert [m.first_name for m in tree['couple']] == ['Adulte']
    assert [m.first_name for m in tree['children']] == ['Enfant']
    # Le membre promu ne doit pas apparaître deux fois.
    assert tree['others'] == []


def test_tree_keeps_a_designated_spouse_as_the_anchor():
    family = Family.objects.create(name='Conjoint seul')
    _member(family, 'Margarette', 'SPOUSE')
    _member(family, 'Maelys', 'CHILD')
    _member(family, 'Invite', 'OTHER')

    tree = _build_household_tree(family.members.all())

    assert [m.first_name for m in tree['couple']] == ['Margarette']
    # L'ancrage de secours ne se déclenche que faute de couple.
    assert [m.first_name for m in tree['others']] == ['Invite']


def test_tree_is_absent_for_an_empty_family():
    family = Family.objects.create(name='Vide')

    tree = _build_household_tree(family.members.all())

    assert tree['has_any'] is False


def test_family_page_renders_the_tree(client):
    user = User.objects.create_superuser(
        username='tree-view', email='tree@example.test',
        password='SecurePass!2026', role='admin',
    )
    family = Family.objects.create(name='Affichee')
    _member(family, 'Jean', 'HEAD')
    _member(family, 'Luc', 'CHILD')
    client.force_login(user)

    response = client.get(reverse('members:family_detail', args=[family.pk]))
    body = response.content.decode('utf-8')

    assert response.status_code == 200
    assert 'Arbre du foyer' in body
    # Le rôle est écrit : le tracé seul ne dit rien à un lecteur d'écran.
    assert 'Chef de famille' in body
