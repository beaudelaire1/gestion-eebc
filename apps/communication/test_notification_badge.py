"""La cloche doit annoncer le nombre de notifications non lues.

Elle renvoyait vers la liste sans jamais dire s'il y avait quelque chose à
lire : il fallait ouvrir la page pour le découvrir.
"""

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.communication.models import Notification
from apps.communication.templatetags.notification_tags import (
    notification_badge,
    unread_notification_count,
)

pytestmark = pytest.mark.django_db


def _user(username='cloche'):
    return User.objects.create_user(
        username=username, email=f'{username}@example.test',
        password='SecurePass!2026', role='admin',
    )


def _notif(user, read=False, title='Nouvelle annonce'):
    return Notification.objects.create(user=user, title=title, is_read=read)


def test_counts_only_unread_notifications():
    user = _user()
    _notif(user)
    _notif(user)
    _notif(user, read=True)

    assert unread_notification_count(user) == 2


def test_ignores_notifications_of_other_users():
    user = _user('cloche-a')
    other = _user('cloche-b')
    _notif(other)

    assert unread_notification_count(user) == 0


def test_anonymous_visitor_counts_zero():
    from django.contrib.auth.models import AnonymousUser

    assert unread_notification_count(AnonymousUser()) == 0


def test_badge_caps_above_ninety_nine():
    assert notification_badge(5) == '5'
    assert notification_badge(99) == '99'
    assert notification_badge(100) == '99+'


def test_badge_is_empty_when_nothing_is_unread():
    assert notification_badge(0) == ''
    assert notification_badge(None) == ''


def test_bell_shows_the_count_and_announces_it(client):
    user = _user('cloche-page')
    _notif(user)
    _notif(user)
    client.force_login(user)

    body = client.get(reverse('dashboard:home')).content.decode('utf-8')

    assert 'notification-badge' in body
    # Un badge est purement visuel : le compte doit aussi être énoncé.
    assert '2 non lues' in body


def test_bell_stays_bare_without_unread_notifications(client):
    user = _user('cloche-vide')
    _notif(user, read=True)
    client.force_login(user)

    body = client.get(reverse('dashboard:home')).content.decode('utf-8')

    assert 'notification-badge' not in body
