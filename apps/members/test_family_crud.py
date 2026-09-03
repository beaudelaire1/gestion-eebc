"""La suppression d'une famille n'existait pas : ni route, ni vue, ni bouton.

On pouvait créer et modifier un foyer, jamais en retirer un. Le lien
member.family étant SET_NULL, supprimer la famille doit détacher ses membres
sans les effacer — c'est la garantie que le test verrouille.
"""

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.core.models import Family
from apps.members.models import Member

pytestmark = pytest.mark.django_db


def _user(role='admin', username='fam-admin'):
    return User.objects.create_user(
        username=username, email=f'{username}@example.test',
        password='SecurePass!2026', role=role,
    )


def _family_with_members():
    family = Family.objects.create(name='Dupont')
    Member.objects.create(first_name='Jean', last_name='Dupont',
                          family=family, family_role='HEAD', status='actif')
    Member.objects.create(first_name='Luc', last_name='Dupont',
                          family=family, family_role='CHILD', status='actif')
    return family


def test_deleting_a_family_keeps_its_members(client):
    client.force_login(_user())
    family = _family_with_members()

    response = client.post(reverse('members:family_delete', args=[family.pk]))

    assert response.status_code == 302
    assert not Family.objects.filter(pk=family.pk).exists()
    # Les personnes restent dans l'annuaire, simplement détachées.
    assert Member.objects.filter(last_name='Dupont').count() == 2
    assert Member.objects.filter(last_name='Dupont', family__isnull=True).count() == 2


def test_confirmation_page_names_the_members_at_stake(client):
    client.force_login(_user(username='fam-confirm'))
    family = _family_with_members()

    body = client.get(
        reverse('members:family_delete', args=[family.pk])
    ).content.decode('utf-8')

    assert 'Jean' in body and 'Luc' in body
    assert 'ne seront pas supprimés' in body


def test_a_plain_member_cannot_delete_a_family(client):
    client.force_login(_user(role='membre', username='fam-membre'))
    family = _family_with_members()

    client.post(reverse('members:family_delete', args=[family.pk]))

    assert Family.objects.filter(pk=family.pk).exists()


def test_family_list_offers_delete_to_an_admin(client):
    client.force_login(_user(username='fam-list'))
    family = _family_with_members()

    body = client.get(reverse('members:family_list')).content.decode('utf-8')

    assert reverse('members:family_delete', args=[family.pk]) in body
