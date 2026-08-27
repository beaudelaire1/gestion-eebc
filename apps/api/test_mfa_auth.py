import pyotp
import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


@pytest.mark.django_db
@override_settings(TWO_FACTOR_ENFORCEMENT_ENABLED=True)
class TestMfaApiAuthentication:
    def test_sensitive_user_without_enrollment_gets_setup_required(self, client):
        User.objects.create_user(
            username='api-finance',
            password='StrongPass123!',
            role='finance',
        )

        response = client.post(
            reverse('api:token_obtain_pair'),
            data={'username': 'api-finance', 'password': 'StrongPass123!'},
            content_type='application/json',
        )
        assert response.status_code == 403
        payload = response.json()
        assert payload['error']['two_factor_setup_required'] is True
        assert payload['error']['setup_url']

    def test_enabled_two_factor_requires_otp_and_marks_tokens(self, client):
        user = User.objects.create_user(
            username='api-admin',
            password='StrongPass123!',
            role='admin',
        )
        user.setup_two_factor()
        secret = user.get_two_factor_secret(migrate_plaintext=False)
        assert user.confirm_two_factor(pyotp.TOTP(secret).now()) is True

        missing = client.post(
            reverse('api:token_obtain_pair'),
            data={'username': 'api-admin', 'password': 'StrongPass123!'},
            content_type='application/json',
        )
        assert missing.status_code == 401
        assert missing.json()['error']['two_factor_required'] is True

        response = client.post(
            reverse('api:token_obtain_pair'),
            data={
                'username': 'api-admin',
                'password': 'StrongPass123!',
                'otp': pyotp.TOTP(secret).now(),
            },
            content_type='application/json',
        )
        assert response.status_code == 200
        refresh = RefreshToken(response.json()['data']['refresh'])
        assert refresh['mfa'] is True
        assert refresh['password_change_only'] is False

    def test_legacy_sensitive_access_token_without_mfa_claim_is_rejected(self, client):
        user = User.objects.create_user(
            username='legacy-jwt',
            password='StrongPass123!',
            role='finance',
        )
        user.setup_two_factor()
        secret = user.get_two_factor_secret(migrate_plaintext=False)
        assert user.confirm_two_factor(pyotp.TOTP(secret).now()) is True

        legacy_refresh = RefreshToken.for_user(user)
        client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {legacy_refresh.access_token}'
        response = client.get(reverse('api:profile'))
        assert response.status_code == 401
        assert response.json()['error']['two_factor_required'] is True

    def test_legacy_sensitive_refresh_token_without_mfa_claim_is_rejected(self, client):
        user = User.objects.create_user(
            username='legacy-refresh',
            password='StrongPass123!',
            role='secretariat',
        )
        user.setup_two_factor()
        secret = user.get_two_factor_secret(migrate_plaintext=False)
        assert user.confirm_two_factor(pyotp.TOTP(secret).now()) is True

        legacy_refresh = RefreshToken.for_user(user)
        response = client.post(
            reverse('api:token_refresh'),
            data={'refresh': str(legacy_refresh)},
            content_type='application/json',
        )
        assert response.status_code == 401
        assert response.json()['two_factor_required'] is True

    def test_password_change_only_token_cannot_access_business_endpoints(self, client):
        user = User.objects.create_user(
            username='temporary-password',
            password='StrongPass123!',
            role='finance',
            must_change_password=True,
        )

        response = client.post(
            reverse('api:token_obtain_pair'),
            data={'username': user.username, 'password': 'StrongPass123!'},
            content_type='application/json',
        )
        assert response.status_code == 200
        access = response.json()['data']['access']

        client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {access}'
        blocked = client.get(reverse('api:profile'))
        assert blocked.status_code == 403
        assert blocked.json()['error']['must_change_password'] is True
