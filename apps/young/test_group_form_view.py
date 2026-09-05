"""Création et modification d'un groupe de jeunesse."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.young.models import YouthGroup


pytestmark = pytest.mark.django_db


@pytest.fixture
def secretariat_client(client):
    user = get_user_model().objects.create_user(
        username='secretariat.jeunesse',
        email='secretariat.jeunesse@example.test',
        password='Secret-pass-123!',
        role='secretariat',
    )
    client.force_login(user)
    return client


@pytest.mark.parametrize('url_name', ['young:group_create', 'young:event_create'])
def test_form_page_has_a_single_form_element(secretariat_client, url_name):
    """Un <form> imbriqué détachait le bouton « Enregistrer » de ses champs.

    ``{% crispy form %}`` sans FormHelper émet sa propre balise <form> : le
    navigateur défaisait l'imbrication et le bouton se retrouvait hors du
    formulaire portant les champs, donc sans effet au clic.
    """
    body = secretariat_client.get(reverse(url_name)).content.decode()

    start = body.index('<form method="post" novalidate>')
    edition_form = body[start:body.index('</form>', start)]

    assert '<form' not in edition_form[len('<form method="post" novalidate>'):]
    assert 'csrfmiddlewaretoken' in edition_form
    assert 'type="submit"' in edition_form


def test_saving_a_new_youth_group(secretariat_client):
    response = secretariat_client.post(
        reverse('young:group_create'),
        {
            'name': 'Ados',
            'min_age': 13,
            'max_age': 17,
            'description': 'Collégiens et lycéens',
            'color': '#6366f1',
            'is_active': 'on',
        },
    )

    group = YouthGroup.objects.get()
    assert response.status_code == 302
    assert response.url == reverse('young:group_list')
    assert group.name == 'Ados'
    assert (group.min_age, group.max_age) == (13, 17)


def test_invalid_age_range_is_reported_on_the_form(secretariat_client):
    response = secretariat_client.post(
        reverse('young:group_create'),
        {'name': 'Impossible', 'min_age': 20, 'max_age': 15, 'color': '#6366f1'},
    )

    assert response.status_code == 200
    assert YouthGroup.objects.count() == 0
    assert response.context['form'].errors
