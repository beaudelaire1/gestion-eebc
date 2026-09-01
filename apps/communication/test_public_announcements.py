"""Les annonces publiques doivent réellement atteindre le site vitrine.

Le champ `visibility` proposait « Public », mais aucune page publique
n'interrogeait le modèle : cocher cette option ne publiait rien.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.communication.models import Announcement
from apps.communication.selectors import get_public_announcements

pytestmark = pytest.mark.django_db


def make(title, **kwargs):
    defaults = {
        'title': title,
        'content': '<p>Bonjour <strong>tout le monde</strong></p>',
        'visibility': Announcement.Visibility.PUBLIC,
        'is_active': True,
    }
    defaults.update(kwargs)
    return Announcement.objects.create(**defaults)


def test_only_public_and_active_announcements_are_selected():
    visible = make('Visible')
    make('Membres', visibility=Announcement.Visibility.MEMBERS)
    make('Equipe', visibility=Announcement.Visibility.STAFF)
    make('Inactive', is_active=False)
    make('Expiree', end_date=timezone.now() - timedelta(days=1))
    make('A venir', start_date=timezone.now() + timedelta(days=1))

    assert list(get_public_announcements()) == [visible]


def test_home_page_shows_a_public_announcement_without_markup(client):
    make('Reunion de priere')

    response = client.get(reverse('public:home'))
    body = response.content.decode()

    assert response.status_code == 200
    assert 'Reunion de priere' in body
    # Le contenu riche doit s'afficher en texte, pas en balises échappées.
    assert 'Bonjour tout le monde' in body
    assert '&lt;p&gt;' not in body


def test_home_page_hides_members_only_announcements(client):
    make('Reserve aux membres', visibility=Announcement.Visibility.MEMBERS)

    body = client.get(reverse('public:home')).content.decode()

    assert 'Reserve aux membres' not in body
