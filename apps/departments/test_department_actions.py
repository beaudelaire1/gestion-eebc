"""Le bouton de création doit rester visible pour un compte multi-rôles.

Le gabarit testait `user.role == 'admin'`. Le champ étant une liste CSV,
l'égalité est fausse dès qu'un compte porte un second rôle : « Nouveau
département » disparaissait pour un administrateur qui gérait aussi les
finances, sans qu'aucune permission ne le lui refuse côté serveur.
"""

import pytest
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def _user(role, username):
    return User.objects.create_user(
        username=username, email=f'{username}@example.test',
        password='SecurePass!2026', role=role,
    )


def test_create_button_shows_for_a_single_role_admin(client):
    client.force_login(_user('admin', 'dept-admin'))

    body = client.get(reverse('departments:list')).content.decode('utf-8')

    assert reverse('departments:create') in body


def test_create_button_shows_for_a_multi_role_admin(client):
    """Le cas signalé : impossible d'ajouter un département depuis la page."""
    client.force_login(_user('admin,finance', 'dept-multi'))

    body = client.get(reverse('departments:list')).content.decode('utf-8')

    assert reverse('departments:create') in body


def test_create_button_stays_hidden_for_a_plain_member(client):
    client.force_login(_user('membre', 'dept-membre'))

    body = client.get(reverse('departments:list')).content.decode('utf-8')

    assert reverse('departments:create') not in body


def test_group_detail_offers_a_way_back_to_the_list(client):
    from apps.groups.models import Group

    client.force_login(_user('admin', 'grp-admin'))
    group = Group.objects.create(name='Chorale')

    body = client.get(reverse('groups:detail', args=[group.pk])).content.decode('utf-8')

    assert reverse('groups:list') in body
    # La suppression existait dans les URL sans être exposée nulle part.
    assert reverse('groups:delete', args=[group.pk]) in body
