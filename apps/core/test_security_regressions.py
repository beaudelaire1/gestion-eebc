"""Regression tests for security boundaries found during the 2026 audit."""
from __future__ import annotations

from datetime import date

import pytest
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.services import AuthenticationService
from apps.core.security import get_trusted_client_ip
from apps.core.upload_security import validate_spreadsheet_upload
from apps.documents.security import validate_document_upload
from apps.events.models import Event
from apps.members.models import Member, VisitationLog

pytestmark = [pytest.mark.django_db, pytest.mark.security]


def make_user(username, role='membre', password='SecurePass!2026', **kwargs):
    return User.objects.create_user(
        username=username,
        email=f'{username}@example.test',
        password=password,
        role=role,
        **kwargs,
    )


def test_secretariat_cannot_promote_account_to_admin(client):
    secretariat = make_user('secretariat', role='secretariat')
    target = make_user('target')
    client.force_login(secretariat)

    response = client.post(reverse('accounts:user_update', kwargs={'user_id': target.pk}), {
        'first_name': 'Target',
        'last_name': 'User',
        'email': target.email,
        'phone': '',
        'roles': ['admin'],
        'is_active': 'on',
    })

    target.refresh_from_db()
    assert response.status_code == 403
    assert 'admin' not in target.get_roles_list()


def test_secretariat_cannot_mutate_existing_admin(client):
    secretariat = make_user('secretariat2', role='secretariat')
    admin = make_user('protected-admin', role='admin')
    client.force_login(secretariat)

    response = client.post(reverse('accounts:user_update', kwargs={'user_id': admin.pk}), {
        'first_name': 'Compromised',
        'last_name': 'Admin',
        'email': admin.email,
        'roles': ['membre'],
        'is_active': 'on',
    })

    admin.refresh_from_db()
    assert response.status_code == 403
    assert admin.first_name != 'Compromised'
    assert admin.has_role('admin')


def test_ordinary_member_cannot_bulk_export_children(client):
    user = make_user('ordinary-export')
    client.force_login(user)
    response = client.get(reverse('imports:export_children'))
    assert response.status_code in (302, 403)


def test_ordinary_member_cannot_download_sensitive_member_pdf(client):
    user = make_user('ordinary-pdf')
    member = Member.objects.create(first_name='Jean', last_name='Secret')
    client.force_login(user)
    response = client.get(reverse('members:print_registration', kwargs={'pk': member.pk}))
    assert response.status_code in (302, 403)


def test_ordinary_member_cannot_open_family_module(client):
    user = make_user('ordinary-family')
    client.force_login(user)
    response = client.get(reverse('members:family_list'))
    assert response.status_code in (302, 403)


def test_confidential_pastoral_visit_hidden_from_encadrant(client):
    encadrant = make_user('encadrant-conf', role='encadrant')
    member = Member.objects.create(first_name='Confidentiel', last_name='Pastoral')
    visit = VisitationLog.objects.create(
        member=member,
        visitor=encadrant,
        is_confidential=True,
        summary='Information pastorale confidentielle',
    )
    client.force_login(encadrant)

    response = client.get(reverse('members:visit_detail', kwargs={'pk': visit.pk}))
    assert response.status_code == 404


def test_confidential_pastoral_visit_visible_to_pastor(client):
    pastor = make_user('pastor-conf', role='pasteur')
    member = Member.objects.create(first_name='Confidentiel', last_name='Pastoral2')
    visit = VisitationLog.objects.create(
        member=member,
        visitor=pastor,
        is_confidential=True,
        summary='Information pastorale confidentielle',
    )
    client.force_login(pastor)

    response = client.get(reverse('members:visit_detail', kwargs={'pk': visit.pk}))
    assert response.status_code == 200
    assert b'Information pastorale confidentielle' in response.content


def test_private_event_hidden_from_non_organizer_web_and_calendar(client):
    owner = make_user('event-owner')
    outsider = make_user('event-outsider')
    private_event = Event.objects.create(
        title='Réunion privée audit',
        start_date=date.today(),
        visibility=Event.Visibility.PRIVATE,
    )
    private_event.organizers.add(owner)
    client.force_login(outsider)

    detail = client.get(reverse('events:detail', kwargs={'pk': private_event.pk}))
    calendar = client.get(reverse('events:calendar_print'))

    assert detail.status_code == 404
    assert calendar.status_code == 200
    assert b'R\xc3\xa9union priv\xc3\xa9e audit' not in calendar.content


def test_private_event_hidden_from_non_organizer_api():
    owner = make_user('event-api-owner')
    outsider = make_user('event-api-outsider')
    private_event = Event.objects.create(
        title='API Private',
        start_date=date.today(),
        visibility=Event.Visibility.PRIVATE,
    )
    private_event.organizers.add(owner)

    api = APIClient()
    api.force_authenticate(outsider)
    response = api.get(reverse('api:event-detail', kwargs={'pk': private_event.pk}))
    assert response.status_code == 404


def test_member_api_exposes_only_minimal_fields_to_ordinary_account():
    user = make_user('directory-user')
    member = Member.objects.create(
        first_name='Marie',
        last_name='Privée',
        email='private@example.test',
        phone='0694000000',
        address='Adresse confidentielle',
        is_baptized=True,
    )
    api = APIClient()
    api.force_authenticate(user)

    response = api.get(reverse('api:member-detail', kwargs={'pk': member.pk}))
    assert response.status_code == 200
    assert response.data['first_name'] == 'Marie'
    for forbidden in ('email', 'phone', 'address', 'date_of_birth', 'marital_status', 'is_baptized', 'family'):
        assert forbidden not in response.data


def test_staff_member_api_keeps_authorized_detail():
    staff = make_user('directory-staff', role='secretariat')
    member = Member.objects.create(
        first_name='Marie',
        last_name='Staff',
        email='staff-visible@example.test',
        phone='0694111111',
    )
    api = APIClient()
    api.force_authenticate(staff)
    response = api.get(reverse('api:member-detail', kwargs={'pk': member.pk}))
    assert response.status_code == 200
    assert response.data['email'] == 'staff-visible@example.test'
    assert response.data['phone'] == '0694111111'


def test_temporary_password_never_mints_jwt():
    user = make_user('temporary-jwt', must_change_password=True)
    api = APIClient()
    response = api.post(reverse('api:token_obtain_pair'), {
        'username': user.username,
        'password': 'SecurePass!2026',
    })
    assert response.status_code == 200
    assert response.data['data']['must_change_password'] is True
    assert 'password_change_challenge' in response.data['data']
    assert 'access' not in response.data['data']
    assert 'refresh' not in response.data['data']


def test_mfa_account_never_mints_jwt_without_second_factor():
    user = make_user(
        'mfa-jwt',
        two_factor_enabled=True,
        two_factor_confirmed=True,
        two_factor_secret='JBSWY3DPEHPK3PXP',
    )
    api = APIClient()
    response = api.post(reverse('api:token_obtain_pair'), {
        'username': user.username,
        'password': 'SecurePass!2026',
    })
    assert response.status_code == 428
    assert response.data['data']['mfa_required'] is True
    assert 'access' not in response.data.get('data', {})
    assert 'refresh' not in response.data.get('data', {})


def test_api_password_change_uses_django_password_validation():
    user = make_user('password-policy')
    api = APIClient()
    api.force_authenticate(user)
    response = api.put(reverse('api:change_password'), {
        'old_password': 'SecurePass!2026',
        'new_password': '12345678',
        'confirm_password': '12345678',
    })
    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password('SecurePass!2026')


def test_password_change_revokes_previous_refresh_token():
    user = make_user('refresh-revoke')
    old_refresh = str(RefreshToken.for_user(user))
    api = APIClient()
    api.force_authenticate(user)

    changed = api.put(reverse('api:change_password'), {
        'old_password': 'SecurePass!2026',
        'new_password': 'An0ther!SecurePass-2026',
        'confirm_password': 'An0ther!SecurePass-2026',
    })
    assert changed.status_code == 200

    anonymous = APIClient()
    refreshed = anonymous.post(reverse('api:token_refresh'), {'refresh': old_refresh})
    assert refreshed.status_code == 401


def test_failed_login_telemetry_does_not_globally_deny_other_ip():
    cache.clear()
    user = make_user('dos-resistant')
    factory = RequestFactory()

    for _ in range(5):
        bad_request = factory.post('/accounts/login/', REMOTE_ADDR='198.51.100.10')
        authenticated, _ = AuthenticationService.authenticate_user(
            user.username,
            'WrongPassword!',
            bad_request,
        )
        assert authenticated is None

    user.refresh_from_db()
    assert user.is_locked() is True  # telemetry remains visible

    good_request = factory.post('/accounts/login/', REMOTE_ADDR='198.51.100.11')
    authenticated, error = AuthenticationService.authenticate_user(
        user.username,
        'SecurePass!2026',
        good_request,
    )
    assert authenticated is not None
    assert error == ''


def test_untrusted_client_cannot_spoof_x_forwarded_for():
    factory = RequestFactory()
    request = factory.get(
        '/',
        REMOTE_ADDR='198.51.100.20',
        HTTP_X_FORWARDED_FOR='203.0.113.99',
    )
    with override_settings(TRUSTED_PROXY_IPS=['127.0.0.1/32']):
        assert get_trusted_client_ip(request) == '198.51.100.20'


def test_trusted_proxy_can_supply_client_address():
    factory = RequestFactory()
    request = factory.get(
        '/',
        REMOTE_ADDR='127.0.0.1',
        HTTP_X_FORWARDED_FOR='203.0.113.10, 127.0.0.1',
    )
    with override_settings(TRUSTED_PROXY_IPS=['127.0.0.1/32']):
        assert get_trusted_client_ip(request) == '203.0.113.10'


def test_active_svg_upload_is_rejected():
    upload = SimpleUploadedFile(
        'malicious.svg',
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        content_type='image/svg+xml',
    )
    with pytest.raises(ValidationError):
        validate_document_upload(upload)


def test_renamed_fake_xlsx_is_rejected_before_parser():
    upload = SimpleUploadedFile(
        'fake.xlsx',
        b'not-a-zip-or-an-excel-file',
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    with pytest.raises(ValidationError):
        validate_spreadsheet_upload(upload, allowed_extensions=('.xlsx',))


def test_state_changing_endpoints_reject_get(client):
    finance = make_user('finance-method', role='finance')
    client.force_login(finance)
    response = client.get(reverse('finance:transaction_validate', kwargs={'pk': 999999}))
    assert response.status_code == 405

    encadrant = make_user('pastoral-method', role='encadrant')
    client.force_login(encadrant)
    response = client.get(reverse('members:life_event_mark_visited', kwargs={'pk': 999999}))
    assert response.status_code == 405


def test_upload_memory_thresholds_are_bounded():
    assert settings.FILE_UPLOAD_MAX_MEMORY_SIZE <= 5 * 1024 * 1024
    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE <= 10 * 1024 * 1024
