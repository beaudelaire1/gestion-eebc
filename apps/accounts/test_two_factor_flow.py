"""Regression tests for the complete browser 2FA flow."""

import pyotp
import pytest
from django.test import override_settings
from django.urls import reverse

from apps.accounts.middleware import MFA_VERIFIED_SESSION_KEY
from apps.core.church import CHURCH_INFO
from apps.accounts.models import User
from apps.accounts.services import AuthenticationService

pytestmark = pytest.mark.django_db


def _make_mfa_user(username, password='SecurePass!2026', **kwargs):
    secret = pyotp.random_base32()
    user = User.objects.create_user(
        username=username,
        email=f'{username}@example.test',
        password=password,
        two_factor_enabled=True,
        two_factor_confirmed=True,
        two_factor_secret=secret,
        **kwargs,
    )
    return user, secret


def _mark_session_verified(client, user):
    session = client.session
    session[MFA_VERIFIED_SESSION_KEY] = str(user.pk)
    session.save()


@override_settings(DEBUG=True, TURNSTILE_SITE_KEY='', RECAPTCHA_PUBLIC_KEY='')
def test_web_login_requires_and_accepts_totp(client):
    user, secret = _make_mfa_user('mfa-browser')

    first_factor = client.post(
        reverse('accounts:login'),
        {'username': user.username, 'password': 'SecurePass!2026'},
        REMOTE_ADDR='198.51.100.31',
    )

    assert first_factor.status_code == 302
    assert first_factor.url == reverse('accounts:two_factor_verify')
    assert client.session['two_factor_user_id'] == user.pk
    assert '_auth_user_id' not in client.session

    second_factor = client.post(
        reverse('accounts:two_factor_verify'),
        {'code': pyotp.TOTP(secret).now()},
        REMOTE_ADDR='198.51.100.31',
    )

    assert second_factor.status_code == 302
    assert second_factor.url == reverse('dashboard:home')
    assert client.session['_auth_user_id'] == str(user.pk)
    assert client.session[MFA_VERIFIED_SESSION_KEY] == str(user.pk)
    assert 'two_factor_user_id' not in client.session


@override_settings(DEBUG=True, TURNSTILE_SITE_KEY='', RECAPTCHA_PUBLIC_KEY='')
def test_backup_code_can_be_entered_and_consumed_in_browser_flow(client):
    user = User.objects.create_user(
        username='mfa-backup',
        email='mfa-backup@example.test',
        password='SecurePass!2026',
    )
    backup_codes = user.setup_two_factor()
    user.two_factor_enabled = True
    user.two_factor_confirmed = True
    user.save(update_fields=['two_factor_enabled', 'two_factor_confirmed'])

    first_factor = client.post(
        reverse('accounts:login'),
        {'username': user.username, 'password': 'SecurePass!2026'},
        REMOTE_ADDR='198.51.100.32',
    )
    assert first_factor.status_code == 302
    assert first_factor.url == reverse('accounts:two_factor_verify')

    challenge = client.get(reverse('accounts:two_factor_verify'))
    assert challenge.status_code == 200
    assert b'maxlength="9"' in challenge.content
    assert b'inputmode="text"' in challenge.content

    backup_code = backup_codes[0]
    assert len(backup_code) == 9

    verified = client.post(
        reverse('accounts:two_factor_verify'),
        {'code': backup_code},
        REMOTE_ADDR='198.51.100.32',
    )

    assert verified.status_code == 302
    assert verified.url == reverse('dashboard:home')
    assert client.session['_auth_user_id'] == str(user.pk)
    assert client.session[MFA_VERIFIED_SESSION_KEY] == str(user.pk)

    user.refresh_from_db()
    assert user.verify_two_factor_code(backup_code) is False


def test_authenticated_mfa_session_without_proof_is_rejected(client):
    """Any authenticated session without factor-two proof must be torn down."""
    user, _ = _make_mfa_user('mfa-session-bypass')
    client.force_login(user)

    response = client.get(reverse('accounts:profile'))

    assert response.status_code == 302
    assert response.url == reverse('accounts:two_factor_verify')
    assert client.session['two_factor_user_id'] == user.pk
    assert '_auth_user_id' not in client.session
    assert MFA_VERIFIED_SESSION_KEY not in client.session


def test_authenticated_mfa_session_with_proof_is_allowed(client):
    user, _ = _make_mfa_user('mfa-session-verified')
    client.force_login(user)
    _mark_session_verified(client, user)

    response = client.get(reverse('accounts:profile'))

    assert response.status_code == 200
    assert client.session['_auth_user_id'] == str(user.pk)


def test_django_admin_session_cannot_bypass_mfa(client):
    """Django admin uses its own login view; middleware must still enforce MFA."""
    user, _ = _make_mfa_user(
        'mfa-admin-bypass',
        is_staff=True,
        is_superuser=True,
    )
    client.force_login(user)

    response = client.get(reverse('admin:index'))

    assert response.status_code == 302
    assert response.url == reverse('accounts:two_factor_verify')
    assert client.session['two_factor_user_id'] == user.pk
    assert '_auth_user_id' not in client.session


def test_backup_codes_management_page_exists_after_verified_session(client):
    user, _ = _make_mfa_user('mfa-backup-page')
    client.force_login(user)
    _mark_session_verified(client, user)

    response = client.get(reverse('accounts:two_factor_backup_codes'))

    assert response.status_code == 200
    assert 'Codes de secours' in response.content.decode('utf-8')


def test_enabling_2fa_marks_current_session_verified(client):
    user = User.objects.create_user(
        username='mfa-enable-session',
        email='mfa-enable-session@example.test',
        password='SecurePass!2026',
    )
    client.force_login(user)

    setup_page = client.get(reverse('accounts:two_factor_setup'))
    assert setup_page.status_code == 200

    user.refresh_from_db()
    code = pyotp.TOTP(user.two_factor_secret).now()
    enabled = client.post(reverse('accounts:two_factor_setup'), {'code': code})

    assert enabled.status_code == 302
    assert enabled.url == reverse('accounts:profile')
    assert client.session[MFA_VERIFIED_SESSION_KEY] == str(user.pk)

    user.refresh_from_db()
    assert user.two_factor_enabled is True
    assert user.two_factor_confirmed is True


def test_required_password_change_cannot_bypass_mfa(client):
    user, _ = _make_mfa_user('mfa-password-change', must_change_password=True)
    token = AuthenticationService.generate_password_change_token(user)
    new_password = 'An0ther!SecurePass-2026'

    response = client.post(
        reverse('accounts:first_login_password_change'),
        {
            'token': token,
            'new_password1': new_password,
            'new_password2': new_password,
        },
    )

    assert response.status_code == 302
    assert response.url == reverse('accounts:two_factor_verify')
    assert client.session['two_factor_user_id'] == user.pk
    assert '_auth_user_id' not in client.session

    user.refresh_from_db()
    assert user.must_change_password is False
    assert user.check_password(new_password)


def test_setup_page_offers_a_scannable_qr_code_to_a_user_without_2fa(client):
    user = User.objects.create_user(
        username='mfa-enrol-qr',
        email='mfa-enrol-qr@example.test',
        password='SecurePass!2026',
    )
    client.force_login(user)

    response = client.get(reverse('accounts:two_factor_setup'))
    body = response.content.decode('utf-8')

    assert response.status_code == 200
    assert 'data:image/png;base64,' in body

    user.refresh_from_db()
    assert user.two_factor_secret
    assert user.two_factor_secret in body
    assert user.two_factor_enabled is False


def test_setup_page_keeps_the_same_secret_across_visits(client):
    user = User.objects.create_user(
        username='mfa-enrol-stable',
        email='mfa-enrol-stable@example.test',
        password='SecurePass!2026',
    )
    client.force_login(user)

    client.get(reverse('accounts:two_factor_setup'))
    user.refresh_from_db()
    first_secret = user.two_factor_secret

    client.get(reverse('accounts:two_factor_setup'))
    user.refresh_from_db()

    # A QR code already scanned in the authenticator app must stay valid.
    assert user.two_factor_secret == first_secret


def test_resumed_enrolment_still_shows_usable_backup_codes(client):
    """An interrupted setup must not activate 2FA without visible recovery codes."""
    user = User.objects.create_user(
        username='mfa-enrol-resume',
        email='mfa-enrol-resume@example.test',
        password='SecurePass!2026',
    )
    client.force_login(user)

    # First visit: the user leaves without confirming.
    client.get(reverse('accounts:two_factor_setup'))

    # Second visit: this is the page the user actually completes.
    second_visit = client.get(reverse('accounts:two_factor_setup'))
    shown_codes = second_visit.context['backup_codes']

    assert second_visit.context['show_backup_codes'] is True
    assert len(shown_codes) == 10

    user.refresh_from_db()
    activated = client.post(
        reverse('accounts:two_factor_setup'),
        {'code': pyotp.TOTP(user.two_factor_secret).now()},
    )
    assert activated.status_code == 302

    user.refresh_from_db()
    assert user.two_factor_enabled is True
    # The codes displayed on the completed page are the ones that work.
    assert user.verify_two_factor_code(shown_codes[0]) is True


# ---------------------------------------------------------------------------
# Mandatory enrolment for privileged roles
# ---------------------------------------------------------------------------

@override_settings(TWO_FACTOR_ENFORCED_FOR_PRIVILEGED_ROLES=True)
def test_privileged_account_without_2fa_is_pushed_to_enrolment(client):
    user = User.objects.create_user(
        username='finance-no-2fa',
        email='finance-no-2fa@example.test',
        password='SecurePass!2026',
        role='finance',
    )
    client.force_login(user)

    response = client.get(reverse('dashboard:home'))

    assert response.status_code == 302
    assert response.url == reverse('accounts:two_factor_setup')


@override_settings(TWO_FACTOR_ENFORCED_FOR_PRIVILEGED_ROLES=True)
def test_enrolment_page_and_logout_stay_reachable_without_2fa(client):
    """The forced redirect must not trap the account in a loop."""
    user = User.objects.create_user(
        username='pasteur-no-2fa',
        email='pasteur-no-2fa@example.test',
        password='SecurePass!2026',
        role='pasteur',
    )
    client.force_login(user)

    setup_page = client.get(reverse('accounts:two_factor_setup'))
    assert setup_page.status_code == 200

    # GET renders the confirmation page, POST performs the logout. Neither
    # step may be swallowed by the forced redirect.
    logout_confirm = client.get(reverse('accounts:logout'))
    assert logout_confirm.status_code == 200

    logged_out = client.post(reverse('accounts:logout'))
    assert logged_out.status_code == 302
    assert logged_out.url != reverse('accounts:two_factor_setup')
    assert '_auth_user_id' not in client.session


@override_settings(TWO_FACTOR_ENFORCED_FOR_PRIVILEGED_ROLES=True)
def test_superuser_without_a_privileged_role_is_still_forced(client):
    user = User.objects.create_superuser(
        username='root-no-2fa',
        email='root-no-2fa@example.test',
        password='SecurePass!2026',
    )
    client.force_login(user)

    response = client.get(reverse('dashboard:home'))

    assert response.status_code == 302
    assert response.url == reverse('accounts:two_factor_setup')


@override_settings(TWO_FACTOR_ENFORCED_FOR_PRIVILEGED_ROLES=True)
def test_plain_member_keeps_2fa_optional(client):
    user = User.objects.create_user(
        username='membre-no-2fa',
        email='membre-no-2fa@example.test',
        password='SecurePass!2026',
        role='membre',
    )
    client.force_login(user)

    response = client.get(reverse('dashboard:home'))

    assert response.status_code == 200


@override_settings(TWO_FACTOR_ENFORCED_FOR_PRIVILEGED_ROLES=True)
def test_privileged_account_is_released_once_enrolled(client):
    user, _ = _make_mfa_user('finance-with-2fa', role='finance')
    client.force_login(user)
    _mark_session_verified(client, user)

    response = client.get(reverse('dashboard:home'))

    assert response.status_code == 200


@override_settings(TWO_FACTOR_ENFORCED_FOR_PRIVILEGED_ROLES=True)
def test_completing_enrolment_ends_the_forced_redirect(client):
    user = User.objects.create_user(
        username='secretariat-enrols',
        email='secretariat-enrols@example.test',
        password='SecurePass!2026',
        role='secretariat',
    )
    client.force_login(user)

    client.get(reverse('accounts:two_factor_setup'))
    user.refresh_from_db()
    client.post(
        reverse('accounts:two_factor_setup'),
        {'code': pyotp.TOTP(user.two_factor_secret).now()},
    )

    user.refresh_from_db()
    assert user.two_factor_enabled is True

    response = client.get(reverse('dashboard:home'))
    assert response.status_code == 200


@override_settings(DEBUG=True, TURNSTILE_SITE_KEY='', RECAPTCHA_PUBLIC_KEY='')
@override_settings(TWO_FACTOR_ENFORCED_FOR_PRIVILEGED_ROLES=True)
def test_privileged_login_lands_on_enrolment_instead_of_dashboard(client):
    User.objects.create_user(
        username='admin-logs-in',
        email='admin-logs-in@example.test',
        password='SecurePass!2026',
        role='admin',
    )

    response = client.post(
        reverse('accounts:login'),
        {'username': 'admin-logs-in', 'password': 'SecurePass!2026'},
        REMOTE_ADDR='198.51.100.40',
    )

    assert response.status_code == 302
    assert response.url == reverse('accounts:two_factor_setup')


@override_settings(TWO_FACTOR_ENFORCED_FOR_PRIVILEGED_ROLES=True)
def test_mobile_jwt_api_is_not_caught_by_the_enrolment_redirect(client):
    """The Flutter app authenticates per request with JWT, not with a session.

    The middleware runs before DRF resolves the bearer token, so it sees an
    anonymous request and must leave it alone. A redirect here would break the
    mobile app for every leader who has not enrolled yet.
    """
    from rest_framework_simplejwt.tokens import RefreshToken

    user = User.objects.create_user(
        username='admin-mobile',
        email='admin-mobile@example.test',
        password='SecurePass!2026',
        role='admin',
    )
    token = RefreshToken.for_user(user).access_token

    response = client.get(
        '/api/v1/profile/',
        HTTP_AUTHORIZATION=f'Bearer {token}',
    )

    assert response.status_code == 200
    assert response['Content-Type'].startswith('application/json')


def test_mobile_jwt_api_works_for_an_account_with_2fa_enabled(client):
    """A leader who enrolled 2FA must keep a working mobile app.

    The session-wide MFA check also runs after the view, where DRF has already
    resolved the bearer token. Without a session-authentication guard it would
    convert a valid API call into a logout plus an HTML redirect.
    """
    from rest_framework_simplejwt.tokens import RefreshToken

    user, _ = _make_mfa_user('admin-mobile-2fa', role='admin')
    token = RefreshToken.for_user(user).access_token

    response = client.get(
        '/api/v1/profile/',
        HTTP_AUTHORIZATION=f'Bearer {token}',
    )

    assert response.status_code == 200
    assert response['Content-Type'].startswith('application/json')


@override_settings(TWO_FACTOR_ENFORCED_FOR_PRIVILEGED_ROLES=True)
def test_forced_enrolment_page_explains_itself_and_offers_support(client):
    user = User.objects.create_user(
        username='ancien-forced',
        email='ancien-forced@example.test',
        password='SecurePass!2026',
        role='ancien',
    )
    client.force_login(user)

    response = client.get(reverse('accounts:two_factor_setup'))
    body = response.content.decode('utf-8')

    assert response.context['enrollment_required'] is True
    assert 'obligatoire pour votre rôle' in body
    # The QR code is the first-time path, support is the way out for anyone
    # who cannot scan it.
    assert 'data:image/png;base64,' in body
    assert CHURCH_INFO['email'] in body
    assert 'mailto:' in body


@override_settings(TWO_FACTOR_ENFORCED_FOR_PRIVILEGED_ROLES=True)
def test_voluntary_enrolment_page_does_not_claim_to_be_mandatory(client):
    user = User.objects.create_user(
        username='membre-volontaire',
        email='membre-volontaire@example.test',
        password='SecurePass!2026',
        role='membre',
    )
    client.force_login(user)

    response = client.get(reverse('accounts:two_factor_setup'))
    body = response.content.decode('utf-8')

    assert response.context['enrollment_required'] is False
    assert 'obligatoire pour votre rôle' not in body
    assert 'data:image/png;base64,' in body


# ---------------------------------------------------------------------------
# Support fallback: resetting an account that lost its authenticator
# ---------------------------------------------------------------------------

def test_reset_2fa_command_lets_a_locked_out_account_enrol_again():
    from django.core.management import call_command

    user, _ = _make_mfa_user('lost-phone', role='finance')
    assert user.two_factor_secret

    call_command('reset_2fa', 'lost-phone')

    user.refresh_from_db()
    assert user.two_factor_enabled is False
    assert user.two_factor_secret == ''
    assert user.two_factor_backup_codes == ''

    # The account can start over from a brand new QR code.
    new_codes = user.start_two_factor_enrollment()
    user.refresh_from_db()
    assert user.two_factor_secret
    assert len(new_codes) == 10


def test_reset_2fa_command_refuses_an_unknown_account():
    from django.core.management import call_command
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command('reset_2fa', 'no-such-user')


def test_reset_2fa_status_reports_without_changing_anything():
    from django.core.management import call_command

    user, secret = _make_mfa_user('status-only', role='admin')

    call_command('reset_2fa', 'status-only', '--status')

    user.refresh_from_db()
    assert user.two_factor_enabled is True
    assert user.two_factor_secret == secret
