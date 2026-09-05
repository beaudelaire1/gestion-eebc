"""Recherche dans la liste des familles."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.core.models import Family
from apps.members.models import Member


pytestmark = pytest.mark.django_db


@pytest.fixture
def secretariat_client(client):
    user = get_user_model().objects.create_user(
        username='secretariat.famille',
        email='secretariat.famille@example.test',
        password='Secret-pass-123!',
        role='secretariat',
    )
    client.force_login(user)
    return client


@pytest.fixture
def families():
    anselme = Family.objects.create(name='Anselme')
    kaline = Family.objects.create(name='Kaline')
    Member.objects.create(first_name='Ruth', last_name='Anselme', family=anselme)
    Member.objects.create(first_name='Josué', last_name='Kaline', family=kaline)
    return {'anselme': anselme, 'kaline': kaline}


def test_search_matches_the_household_name(secretariat_client, families):
    response = secretariat_client.get(
        reverse('members:family_list'), {'search': 'kalin'}
    )

    assert list(response.context['families']) == [families['kaline']]


def test_search_matches_a_person_of_the_household(secretariat_client, families):
    """Le nom du foyer n'est pas toujours celui qu'on a en tête."""
    response = secretariat_client.get(
        reverse('members:family_list'), {'search': 'Ruth'}
    )

    assert list(response.context['families']) == [families['anselme']]


def test_htmx_search_returns_only_the_list_fragment(secretariat_client, families):
    """La cible #family-content ne doit pas recevoir la page entière."""
    response = secretariat_client.get(
        reverse('members:family_list'),
        {'search': 'kalin'},
        HTTP_HX_REQUEST='true',
    )
    body = response.content.decode()

    assert response.templates[0].name == 'members/partials/family_list_content.html'
    assert 'id="family-content"' not in body
    assert 'Kaline' in body
    assert 'Anselme' not in body


def test_full_page_keeps_the_htmx_target(secretariat_client, families):
    body = secretariat_client.get(reverse('members:family_list')).content.decode()

    assert 'id="family-content"' in body
    assert 'id="family-loading"' in body
