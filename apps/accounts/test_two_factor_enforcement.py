import pyotp
import pytest
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.two_factor_security import ENCRYPTED_PREFIX, requires_two_factor


@pytest.mark.django_db
class TestTwoFactorSecurity:
    def test_sensitive_roles_require_two_factor(self):
        for role in ('admin', 'finance', 'secretariat', 'pasteur', 'moniteur', 'chauffeur'):
            user = User.objects.create_user(
                username=f'user-{role}',
                password='StrongPass123!',
                role=role,
            )
            assert requires_two_factor(user) is True

        member = User.objects.create_user(
            username='plain-member',
            password='StrongPass123!',
            role='membre',
        )
        assert requires_two_factor(member) is False

    def test_totp_secret_is_encrypted_at_rest(self):
        user = User.objects.create_user(
            username='encrypted-secret',
            password='StrongPass123!',
            role='admin',
        )
        user.setup_two_factor()
        user.refresh_from_db()

        assert user.two_factor_secret.startswith(ENCRYPTED_PREFIX)
        plaintext = user.get_two_factor_secret(migrate_plaintext=False)
        assert plaintext
        assert plaintext not in user.two_factor_secret

    def test_legacy_plaintext_secret_is_migrated_on_read(self):
        plaintext = pyotp.random_base32()
        user = User.objects.create_user(
            username='legacy-secret',
            password='StrongPass123!',
            role='admin',
            two_factor_secret=plaintext,
        )

        assert user.get_two_factor_secret() == plaintext
        user.refresh_from_db()
        assert user.two_factor_secret.startswith(ENCRYPTED_PREFIX)


@pytest.mark.django_db
@override_settings(TWO_FACTOR_ENFORCEMENT_ENABLED=True)
class TestTwoFactorWebEnforcement:
    def test_sensitive_session_without_2fa_is_forced_to_enroll(self, client):
        admin = User.objects.create_user(
            username='web-admin',
            password='StrongPass123!',
            role='admin',
            is_staff=True,
        )
        client.force_login(admin)

        response = client.get(reverse('dashboard:home'))
        assert response.status_code == 302
        assert response.url == reverse('accounts:two_factor_setup')

    def test_enabled_2fa_requires_challenge_for_existing_session(self, client):
        admin = User.objects.create_user(
            username='web-mfa-admin',
            password='StrongPass123!',
            role='admin',
            is_staff=True,
        )
        admin.setup_two_factor()
        secret = admin.get_two_factor_secret(migrate_plaintext=False)
        assert admin.confirm_two_factor(pyotp.TOTP(secret).now()) is True

        client.force_login(admin)
        response = client.get(reverse('dashboard:home'))
        assert response.status_code == 302
        assert response.url == reverse('accounts:two_factor_verify')

        response = client.post(
            reverse('accounts:two_factor_verify'),
            {'code': pyotp.TOTP(secret).now()},
        )
        assert response.status_code == 302

        session = client.session
        assert session['two_factor_verified_user_id'] == admin.pk

    def test_required_account_cannot_disable_2fa(self, client):
        admin = User.objects.create_user(
            username='cannot-disable',
            password='StrongPass123!',
            role='admin',
            is_staff=True,
        )
        admin.setup_two_factor()
        secret = admin.get_two_factor_secret(migrate_plaintext=False)
        assert admin.confirm_two_factor(pyotp.TOTP(secret).now()) is True

        client.force_login(admin)
        session = client.session
        session['two_factor_verified_user_id'] = admin.pk
        session.save()

        response = client.post(
            reverse('accounts:two_factor_disable'),
            {'code': pyotp.TOTP(secret).now()},
        )
        assert response.status_code == 302
        admin.refresh_from_db()
        assert admin.two_factor_enabled is True

    def test_admin_route_is_guarded_by_same_mfa_policy(self, client):
        admin = User.objects.create_superuser(
            username='django-admin',
            email='admin@example.com',
            password='StrongPass123!',
        )
        client.force_login(admin)

        response = client.get('/gestion-eebc/')
        assert response.status_code == 302
        assert response.url == reverse('accounts:two_factor_setup')
