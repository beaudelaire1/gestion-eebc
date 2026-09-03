"""Regression tests for the complete browser 2FA flow."""

import pyotp
import pytest
from django.test import override_settings
from django.urls import reverse

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

    user.refresh_from_db()
    assert user.verify_two_factor_code(backup_code) is False


def test_backup_codes_management_page_exists(client):
    user, _ = _make_mfa_user('mfa-backup-page')
    client.force_login(user)

    response = client.get(reverse('accounts:two_factor_backup_codes'))

    assert response.status_code == 200
    assert 'Codes de secours' in response.content.decode('utf-8')


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
