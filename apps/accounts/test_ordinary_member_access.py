import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.communication.models import Announcement
from apps.dashboard.services import DashboardService


pytestmark = pytest.mark.django_db


@pytest.fixture
def ordinary_member():
    return get_user_model().objects.create_user(
        username='simple.member',
        email='member@example.test',
        password='Member-pass-123!',
        first_name='Simple',
        role='membre',
    )


@pytest.fixture
def member_client(client, ordinary_member):
    client.force_login(ordinary_member)
    return client


def test_member_dashboard_does_not_load_management_statistics(
    member_client, monkeypatch
):
    def fail_if_called(*args, **kwargs):
        raise AssertionError('management statistics must not be loaded')

    monkeypatch.setattr(
        DashboardService, 'get_member_stats', fail_if_called
    )

    response = member_client.get(reverse('dashboard:home'))

    assert response.status_code == 200
    assert response.templates[0].name == 'dashboard/member_home.html'
    body = response.content.decode()
    assert 'Mon espace' in body
    assert 'Trésorerie' not in body
    assert 'app-search' not in body


def test_member_sidebar_only_shows_member_services(member_client):
    body = member_client.get(reverse('dashboard:home')).content.decode()

    assert 'data-nav-section="principal"' in body
    assert 'data-nav-section="communication"' in body
    assert 'Notifications' in body
    assert 'Annonces' in body
    for section in (
        'vie-d-eglise',
        'finances',
        'gestion',
        'jeunesse',
        'club-biblique',
        'transport',
        'ressources',
        'documents',
        'site-web-cms',
        'administration',
    ):
        assert f'data-nav-section="{section}"' not in body
    assert 'Composer un e-mail' not in body
    assert 'Historique emails' not in body


@pytest.mark.parametrize('url_name', [
    'members:list',
    'finance:dashboard',
    'young:home',
    'accounts:user_list',
    'imports:hub',
    'events:create',
    'dashboard:stats',
    'dashboard:search',
    'communication:email_compose',
])
def test_member_cannot_open_management_urls(member_client, url_name):
    response = member_client.get(reverse(url_name))

    assert response.status_code == 403


@pytest.mark.parametrize('url_name', [
    'dashboard:home',
    'accounts:profile',
    'events:calendar',
    'communication:notifications',
    'communication:announcements',
])
def test_member_can_open_self_service_urls(member_client, url_name):
    response = member_client.get(reverse(url_name))

    assert response.status_code == 200


def test_member_cannot_see_staff_announcements(member_client, ordinary_member):
    member_announcement = Announcement.objects.create(
        title='Annonce membres',
        content='Visible par les membres.',
        visibility=Announcement.Visibility.MEMBERS,
        created_by=ordinary_member,
    )
    staff_announcement = Announcement.objects.create(
        title='Annonce équipe',
        content='Réservée aux responsables.',
        visibility=Announcement.Visibility.STAFF,
        created_by=ordinary_member,
    )

    listing = member_client.get(reverse('communication:announcements'))
    hidden_detail = member_client.get(
        reverse('communication:announcement_detail', args=[staff_announcement.pk])
    )

    assert member_announcement.title in listing.content.decode()
    assert staff_announcement.title not in listing.content.decode()
    assert hidden_detail.status_code == 404
