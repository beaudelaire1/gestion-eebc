"""Regression tests for the complete browser 2FA flow."""

import pyotp
import pytest
from django.test import override_settings
from django.urls import reverse

from apps.accounts.middleware import MFA_VERIFIED_SESSION_KEY
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
