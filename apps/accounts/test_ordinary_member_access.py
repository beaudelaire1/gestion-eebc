from datetime import date, time

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.communication.models import Announcement
from apps.core.models import Testimony
from apps.documents.models import Document
from apps.dashboard.services import DashboardService
from apps.members.models import Member
from apps.transport.models import TransportRequest
from apps.young.models import YoungMember


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


@pytest.fixture
def young_profile(ordinary_member):
    """Jeune non membre de l'église : un compte, aucune fiche membre."""
    return YoungMember.objects.create(
        first_name='Jeune',
        last_name='Sansfiche',
        date_of_birth=date(2010, 5, 12),
        gender=YoungMember.Gender.MASCULIN,
        user=ordinary_member,
        phone='0694222222',
        address='3 rue des Flamboyants',
        city='Cayenne',
        postal_code='97300',
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


def test_member_sidebar_shows_the_non_restricted_sections(member_client):
    body = member_client.get(reverse('dashboard:home')).content.decode()

    for section in (
        'principal',
        'mes-services',
        'vie-d-eglise',
        'transport',
        'documents',
        'communication',
    ):
        assert f'data-nav-section="{section}"' in body
    for section in (
        'finances',
        'gestion',
        'jeunesse',
        'club-biblique',
        'ressources',
        'site-web-cms',
        'administration',
    ):
        assert f'data-nav-section="{section}"' not in body


def test_member_sidebar_hides_the_management_entries_of_open_sections(member_client):
    """Une rubrique ouverte garde ses écrans réservés hors de portée."""
    body = member_client.get(reverse('dashboard:home')).content.decode()

    for url_name in (
        'transport:drivers',
        'transport:driver_create',
        'transport:calendar',
        'documents:upload',
        'documents:categories',
        'documents:stats',
        'documents:generated_list',
        'worship:service_create',
        'communication:email_compose',
        'communication:email_logs',
        'dashboard:search',
    ):
        assert reverse(url_name) not in body


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


def _transport_payload(**overrides):
    payload = {
        'request_type': TransportRequest.RequestType.CLUB,
        'requester_name': 'Jeune Sansfiche',
        'requester_phone': '0694222222',
        'pickup_address': '3 rue des Flamboyants',
        'event_date': date.today().isoformat(),
        'event_time': '09:00',
        'passengers_count': 1,
    }
    payload.update(overrides)
    return payload


def test_young_without_church_record_keeps_access_to_their_request(
    member_client, young_profile
):
    """Un jeune non membre a un compte mais aucune fiche membre."""
    member_client.post(reverse('transport:request_create'), _transport_payload())

    transport_request = TransportRequest.objects.get()
    listing = member_client.get(reverse('transport:requests'))
    detail = member_client.get(
        reverse('transport:request_detail', args=[transport_request.pk])
    )

    assert transport_request.requester_member is None
    assert transport_request.requester_young == young_profile
    assert transport_request.requester_name in listing.content.decode()
    assert detail.status_code == 200


def test_young_who_is_also_a_church_member_is_attached_to_both_records(
    member_client, member_profile, young_profile
):
    young_profile.linked_member = member_profile
    young_profile.save(update_fields=['linked_member'])

    member_client.post(reverse('transport:request_create'), _transport_payload())

    transport_request = TransportRequest.objects.get()
    assert transport_request.requester_member == member_profile
    assert transport_request.requester_young == young_profile


def test_young_cannot_reach_the_request_of_another_young(
    member_client, young_profile
):
    other_young = YoungMember.objects.create(
        first_name='Autre',
        last_name='Jeune',
        date_of_birth=date(2011, 3, 4),
        gender=YoungMember.Gender.FEMININ,
    )
    foreign = TransportRequest.objects.create(
        requester_young=other_young,
        requester_name='Autre Jeune',
        requester_phone='0694333333',
        pickup_address='9 rue Voisine',
        event_date=date.today(),
        event_time=time(8, 0),
    )

    listing = member_client.get(reverse('transport:requests'))
    detail = member_client.get(
        reverse('transport:request_detail', args=[foreign.pk])
    )

    assert foreign.requester_name not in listing.content.decode()
    assert detail.status_code == 302


def test_transport_form_prefills_from_the_youth_record(member_client, young_profile):
    body = member_client.get(reverse('transport:request_create')).content.decode()

    assert young_profile.full_name in body
    assert young_profile.address in body


def _create_document(title, *, visibility, uploaded_by, is_confidential=False):
    content = b"Document de test"
    return Document.objects.create(
        title=title,
        file=SimpleUploadedFile(f'{title}.txt', content, content_type='text/plain'),
        file_name=f'{title}.txt',
        file_size=len(content),
        file_type='text/plain',
        media_type=Document.MediaType.DOCUMENT,
        visibility=visibility,
        is_confidential=is_confidential,
        uploaded_by=uploaded_by,
    )


@pytest.fixture
def documents_librarian():
    return get_user_model().objects.create_user(
        username='librarian',
        email='librarian@example.test',
        password='Lib-pass-123!',
        role='secretariat',
    )


def test_member_document_library_is_limited_to_public_files(
    member_client, documents_librarian, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    public = _create_document(
        'note-publique',
        visibility=Document.Visibility.PUBLIC,
        uploaded_by=documents_librarian,
    )
    staff_only = _create_document(
        'note-equipe',
        visibility=Document.Visibility.STAFF,
        uploaded_by=documents_librarian,
    )
    confidential = _create_document(
        'note-confidentielle',
        visibility=Document.Visibility.PUBLIC,
        uploaded_by=documents_librarian,
        is_confidential=True,
    )

    listing = member_client.get(reverse('documents:list'))
    body = listing.content.decode()

    assert listing.status_code == 200
    assert public.title in body
    assert staff_only.title not in body
    assert confidential.title not in body
    assert member_client.get(
        reverse('documents:detail', args=[public.pk])
    ).status_code == 200
    assert member_client.get(
        reverse('documents:detail', args=[staff_only.pk])
    ).status_code == 404
    assert member_client.get(
        reverse('documents:download', args=[staff_only.pk])
    ).status_code == 404


def test_member_does_not_see_who_else_opened_a_document(
    member_client, documents_librarian, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    public = _create_document(
        'note-publique',
        visibility=Document.Visibility.PUBLIC,
        uploaded_by=documents_librarian,
    )

    response = member_client.get(reverse('documents:detail', args=[public.pk]))

    assert response.status_code == 200
    assert not response.context['access_logs']
    assert not response.context['shares']


@pytest.mark.parametrize('url_name', [
    'documents:upload',
    'documents:categories',
    'documents:stats',
    'documents:generated_list',
    'transport:calendar',
    'inventory:list',
])
def test_member_cannot_reach_the_management_side_of_open_sections(
    member_client, url_name
):
    assert member_client.get(reverse(url_name)).status_code == 403


@pytest.fixture
def worship_manager():
    return get_user_model().objects.create_user(
        username='worship.lead',
        email='worship@example.test',
        password='Worship-pass-123!',
        role='responsable_groupe',
    )


def _monthly_schedule(status, site):
    from apps.worship.models import MonthlySchedule

    return MonthlySchedule.objects.create(
        year=2026,
        month=9 if status == MonthlySchedule.Status.PUBLIE else 10,
        site=site,
        status=status,
    )


@pytest.fixture
def church_site():
    from apps.core.models import Site

    site, _ = Site.objects.get_or_create(code='CAY', defaults={'name': 'Cayenne'})
    return site


def test_member_only_reads_published_worship_schedules(member_client, church_site):
    from apps.worship.models import MonthlySchedule

    published = _monthly_schedule(MonthlySchedule.Status.PUBLIE, church_site)
    draft = _monthly_schedule(MonthlySchedule.Status.BROUILLON, church_site)

    listing = member_client.get(reverse('worship:schedule_list'))
    published_detail = member_client.get(
        reverse('worship:schedule_detail', args=[published.pk])
    )
    draft_detail = member_client.get(
        reverse('worship:schedule_detail', args=[draft.pk])
    )

    assert listing.status_code == 200
    assert list(listing.context['schedules']) == [published]
    assert published_detail.status_code == 200
    assert draft_detail.status_code == 404


def test_member_cannot_answer_for_someone_else_worship_slot(
    member_client, other_member
):
    """Confirmer un service à la place d'un autre n'a jamais été contrôlé."""
    from apps.events.models import Event
    from apps.worship.models import ServiceRole, WorshipService

    event = Event.objects.create(title='Culte du dimanche', start_date=date.today())
    service = WorshipService.objects.create(
        event=event,
        service_type=WorshipService.ServiceType.CULTE_DOMINICAL,
    )
    someone_else = ServiceRole.objects.create(
        service=service,
        role=ServiceRole.RoleType.AUTRE,
        member=other_member,
    )

    response = member_client.post(
        reverse('worship:role_confirm', args=[someone_else.pk])
    )
    someone_else.refresh_from_db()

    assert response.status_code == 403
    assert someone_else.status == ServiceRole.Status.EN_ATTENTE


def test_member_answers_for_their_own_worship_slot(member_client, member_profile):
    from apps.events.models import Event
    from apps.worship.models import ServiceRole, WorshipService

    event = Event.objects.create(title='Culte du dimanche', start_date=date.today())
    service = WorshipService.objects.create(
        event=event,
        service_type=WorshipService.ServiceType.CULTE_DOMINICAL,
    )
    own_role = ServiceRole.objects.create(
        service=service,
        role=ServiceRole.RoleType.AUTRE,
        member=member_profile,
    )

    response = member_client.post(reverse('worship:role_confirm', args=[own_role.pk]))
    own_role.refresh_from_db()

    assert response.status_code in (200, 302)
    assert own_role.status == ServiceRole.Status.CONFIRME
