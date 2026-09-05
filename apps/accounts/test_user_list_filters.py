"""Filtres de la liste des comptes utilisateurs."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_user(
        username='team.admin',
        email='team.admin@example.test',
        password='Admin-pass-123!',
        role='admin',
    )
    client.force_login(user)
    return client


@pytest.fixture
def accounts():
    User = get_user_model()
    return {
        'finance': User.objects.create_user(
            username='paul.finance',
            email='paul@example.test',
            password='Pass-123456!',
            first_name='Paul',
            last_name='Comptable',
            role='admin,finance',
        ),
        'member': User.objects.create_user(
            username='rita.membre',
            email='rita@example.test',
            password='Pass-123456!',
            first_name='Rita',
            last_name='Membre',
            role='membre',
        ),
        'invited': User.objects.create_user(
            username='sam.invite',
            email='sam@example.test',
            password='Pass-123456!',
            first_name='Sam',
            last_name='Invite',
            role='membre',
            must_change_password=True,
        ),
    }


def _listed(response):
    return set(response.context['users'].object_list)


def test_search_matches_name_username_and_email(admin_client, accounts):
    response = admin_client.get(reverse('accounts:user_list'), {'q': 'rita@'})

    assert _listed(response) == {accounts['member']}


def test_role_filter_matches_an_account_holding_several_roles(admin_client, accounts):
    """``role`` est une liste séparée par des virgules : « admin,finance »."""
    response = admin_client.get(reverse('accounts:user_list'), {'role': 'finance'})

    assert _listed(response) == {accounts['finance']}


def test_status_filter_separates_pending_invitations(admin_client, accounts):
    pending = admin_client.get(reverse('accounts:user_list'), {'status': 'pending'})
    active = admin_client.get(reverse('accounts:user_list'), {'status': 'active'})

    assert _listed(pending) == {accounts['invited']}
    assert accounts['invited'] not in _listed(active)
    assert accounts['member'] in _listed(active)


def test_filters_combine(admin_client, accounts):
    response = admin_client.get(
        reverse('accounts:user_list'), {'role': 'membre', 'status': 'active'}
    )

    assert _listed(response) == {accounts['member']}
