from datetime import date, time

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.communication.models import Announcement
from apps.core.models import Testimony
from apps.dashboard.services import DashboardService
from apps.members.models import Member
from apps.transport.models import TransportRequest


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


@pytest.fixture
def member_profile(ordinary_member):
    return Member.objects.create(
        first_name='Simple',
        last_name='Membre',
        user=ordinary_member,
    )


@pytest.fixture
def other_member():
    return Member.objects.create(
        first_name='Autre',
        last_name='Membre',
    )


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
    'transport:drivers',
    'campaigns:donate_general',
    'campaigns:list',
    'public_cms:testimony_list',
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
    'transport:requests',
    'transport:request_create',
    'public_cms:testimony_share',
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


def test_member_home_offers_the_self_service_actions(member_client):
    body = member_client.get(reverse('dashboard:home')).content.decode()

    assert reverse('transport:request_create') in body
    assert reverse('public_cms:testimony_share') in body
    assert reverse('public:donation') in body


def test_member_donation_page_stays_outside_the_finance_module(member_client):
    """Le don passe par la page publique Stripe, pas par le module finance."""
    donation_page = member_client.get(reverse('public:donation'))
    finance_module = member_client.get(reverse('finance:dashboard'))

    assert donation_page.status_code == 200
    assert finance_module.status_code == 403


def test_member_testimony_is_stored_unpublished_for_review(
    member_client, member_profile
):
    response = member_client.post(
        reverse('public_cms:testimony_share'),
        {
            'title': 'Ma reconnaissance',
            'content': "Je veux témoigner de ce que Dieu a fait cette année.",
        },
    )

    testimony = Testimony.objects.get()
    assert response.status_code == 302
    assert testimony.is_published is False
    assert testimony.is_featured is False
    assert testimony.member == member_profile
    assert testimony.author_name == member_profile.full_name


def test_member_transport_request_is_bound_to_their_own_profile(
    member_client, member_profile, other_member
):
    response = member_client.post(
        reverse('transport:request_create'),
        {
            'request_type': TransportRequest.RequestType.CULTE,
            # Tentative de déposer la demande au nom d'un autre membre.
            'requester_member': other_member.pk,
            'requester_name': 'Simple Membre',
            'requester_phone': '0694000000',
            'pickup_address': '1 rue des Palmiers',
            'event_date': date.today().isoformat(),
            'event_time': '09:00',
            'passengers_count': 1,
        },
    )

    transport_request = TransportRequest.objects.get()
    assert response.status_code == 302
    assert transport_request.requester_member == member_profile


def test_member_transport_list_only_shows_their_own_requests(
    member_client, member_profile, other_member
):
    own = TransportRequest.objects.create(
        requester_member=member_profile,
        requester_name='Simple Membre',
        requester_phone='0694000000',
        pickup_address='1 rue des Palmiers',
        event_date=date.today(),
        event_time=time(9, 0),
    )
    foreign = TransportRequest.objects.create(
        requester_member=other_member,
        requester_name='Autre Membre',
        requester_phone='0694111111',
        pickup_address='2 rue des Manguiers',
        event_date=date.today(),
        event_time=time(10, 0),
    )

    body = member_client.get(reverse('transport:requests')).content.decode()

    assert own.requester_name in body
    assert foreign.requester_name not in body
    assert reverse('transport:drivers') not in body
