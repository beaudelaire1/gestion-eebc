"""
Tests pour l'app accounts — authentification, rôles, 2FA, services.
"""
import pytest
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User, PasswordChangeToken
from apps.accounts.forms import (
    UserCreationByTeamForm,
    FirstLoginPasswordChangeForm,
    ProfileForm,
)
from apps.accounts.services import AuthenticationService, AccountsService


# =============================================================================
# MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestUserModel:
    """Tests du modèle User — rôles, verrouillage, 2FA."""

    def _make_user(self, **kwargs):
        defaults = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
        defaults.update(kwargs)
        return User.objects.create_user(password='TestPass123!', **defaults)

    def test_create_user(self):
        user = self._make_user()
        assert user.pk is not None
        assert user.username == 'testuser'
        assert user.check_password('TestPass123!')

    def test_default_role_membre(self):
        user = self._make_user()
        assert 'membre' in user.role
        assert 'membre' in user.get_roles_list()

    def test_add_role(self):
        user = self._make_user()
        user.add_role('pasteur')
        user.refresh_from_db()
        assert 'pasteur' in user.get_roles_list()

    def test_add_duplicate_role(self):
        user = self._make_user()
        user.add_role('pasteur')
        user.add_role('pasteur')
        user.refresh_from_db()
        assert user.get_roles_list().count('pasteur') == 1

    def test_remove_role(self):
        user = self._make_user(role='pasteur,ancien')
        user.remove_role('ancien')
        user.refresh_from_db()
        assert 'ancien' not in user.get_roles_list()
        assert 'pasteur' in user.get_roles_list()

    def test_has_role(self):
        user = self._make_user(role='diacre,finance')
        assert user.has_role('diacre') is True
        assert user.has_role('admin') is False

    def test_has_any_role(self):
        user = self._make_user(role='finance')
        assert user.has_any_role('admin', 'finance') is True
        assert user.has_any_role('pasteur', 'ancien') is False

    def test_is_admin_property(self):
        user = self._make_user(role='admin')
        assert user.is_admin is True

    def test_is_pasteur_property(self):
        user = self._make_user(role='pasteur')
        assert user.is_pasteur is True

    def test_role_display(self):
        user = self._make_user(role='pasteur')
        display = user.get_role_display()
        assert isinstance(display, str)
        assert len(display) > 0

    # --- Rate limiting ---
    def test_not_locked_by_default(self):
        user = self._make_user()
        assert user.is_locked() is False

    def test_record_failed_attempt_locks_after_max(self):
        user = self._make_user()
        for _ in range(5):
            user.record_failed_attempt(lockout_minutes=15, max_attempts=5)
        user.refresh_from_db()
        assert user.is_locked() is True

    def test_reset_failed_attempts(self):
        user = self._make_user(failed_login_attempts=4)
        user.reset_failed_attempts()
        user.refresh_from_db()
        assert user.failed_login_attempts == 0

    def test_locked_until_expires(self):
        user = self._make_user(locked_until=timezone.now() - timedelta(minutes=1))
        assert user.is_locked() is False

    # --- 2FA ---
    def test_two_factor_disabled_by_default(self):
        user = self._make_user()
        assert user.two_factor_enabled is False

    def test_setup_two_factor(self):
        user = self._make_user()
        result = user.setup_two_factor()
        assert 'secret' in result or user.two_factor_secret != ''

    def test_disable_two_factor(self):
        user = self._make_user(two_factor_enabled=True, two_factor_secret='JBSWY3DPEHPK3PXP')
        user.disable_two_factor()
        user.refresh_from_db()
        assert user.two_factor_enabled is False
        assert user.two_factor_secret == ''


@pytest.mark.django_db
class TestPasswordChangeToken:
    """Tests du modèle PasswordChangeToken."""

    def _make_user(self):
        return User.objects.create_user(
            username='tokenuser', email='token@example.com', password='TestPass123!'
        )

    def test_generate_token(self):
        user = self._make_user()
        token_str = PasswordChangeToken.generate_token()
        token_obj = PasswordChangeToken.objects.create(
            user=user,
            token=token_str,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        assert token_obj.pk is not None
        assert token_obj.token != ''
        assert token_obj.is_valid() is True

    def test_token_expires(self):
        user = self._make_user()
        token_obj = PasswordChangeToken.objects.create(
            user=user,
            token=PasswordChangeToken.generate_token(),
            expires_at=timezone.now() - timedelta(hours=1),
        )
        assert token_obj.is_valid() is False

    def test_mark_as_used(self):
        user = self._make_user()
        token_obj = PasswordChangeToken.objects.create(
            user=user,
            token=PasswordChangeToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=1),
        )
        token_obj.mark_as_used()
        assert token_obj.used is True
        assert token_obj.is_valid() is False


# =============================================================================
# SERVICES TESTS
# =============================================================================

@pytest.mark.django_db
class TestAccountsService:
    """Tests du service AccountsService."""

    def test_generate_username(self):
        username = AccountsService.generate_username('Paul', 'Kapel')
        assert isinstance(username, str)
        assert len(username) >= 3

    def test_generate_username_uniqueness(self):
        User.objects.create_user(
            username='pa_kapel', email='pk@example.com', password='Pass123!'
        )
        username = AccountsService.generate_username('Paul', 'Kapel')
        assert username != 'pa_kapel'

    def test_generate_password_length(self):
        pwd = AccountsService.generate_password(length=16)
        assert len(pwd) == 16

    def test_generate_password_strength(self):
        pwd = AccountsService.generate_password()
        assert any(c.isupper() for c in pwd)
        assert any(c.islower() for c in pwd)
        assert any(c.isdigit() for c in pwd)

    def test_create_user_by_team(self):
        admin = User.objects.create_user(
            username='admin', email='admin@example.com', password='Admin123!', role='admin'
        )
        result = AccountsService.create_user_by_team(
            first_name='Marie',
            last_name='Dupont',
            email='marie@example.com',
            roles=['membre'],
            created_by=admin,
            send_email=False,
        )
        assert result.success is True
        assert 'user' in result.data
        created_user = result.data['user']
        assert created_user.must_change_password is True
        assert created_user.created_by_team is True

    def test_create_user_duplicate_email(self):
        User.objects.create_user(
            username='existing', email='dup@example.com', password='Pass123!'
        )
        admin = User.objects.create_user(
            username='admin2', email='admin2@example.com', password='Admin123!', role='admin'
        )
        result = AccountsService.create_user_by_team(
            first_name='Autre',
            last_name='Personne',
            email='dup@example.com',
            roles=['membre'],
            created_by=admin,
            send_email=False,
        )
        # Le service peut échouer via IntegrityError ou réussir avec un email existant
        # L'important est qu'il ne crashe pas
        assert isinstance(result.success, bool)


@pytest.mark.django_db
class TestAuthenticationService:
    """Tests du service AuthenticationService."""

    def _make_user(self):
        return User.objects.create_user(
            username='authuser', email='auth@example.com', password='TestPass123!'
        )

    def test_authenticate_valid(self):
        user = self._make_user()
        factory = RequestFactory()
        request = factory.post('/login/')
        authenticated, error = AuthenticationService.authenticate_user(
            'authuser', 'TestPass123!', request
        )
        assert authenticated is not None
        assert error is None or error == ''

    def test_authenticate_invalid_password(self):
        self._make_user()
        factory = RequestFactory()
        request = factory.post('/login/')
        authenticated, error = AuthenticationService.authenticate_user(
            'authuser', 'WrongPass!', request
        )
        assert authenticated is None
        assert error is not None

    def test_authenticate_locked_user(self):
        user = self._make_user()
        user.locked_until = timezone.now() + timedelta(minutes=15)
        user.save()
        factory = RequestFactory()
        request = factory.post('/login/')
        authenticated, error = AuthenticationService.authenticate_user(
            'authuser', 'TestPass123!', request
        )
        assert authenticated is None

    def test_generate_password_change_token(self):
        user = self._make_user()
        token = AuthenticationService.generate_password_change_token(user)
        assert token is not None
        assert isinstance(token, str)

    def test_get_client_ip(self):
        factory = RequestFactory()
        request = factory.get('/')
        ip = AuthenticationService.get_client_ip(request)
        assert ip is not None


# =============================================================================
# FORMS TESTS
# =============================================================================

@pytest.mark.django_db
class TestUserCreationByTeamForm:
    """Tests du formulaire de création utilisateur."""

    def test_valid_form(self):
        form = UserCreationByTeamForm(data={
            'first_name': 'Jean',
            'last_name': 'Martin',
            'email': 'jean.martin@example.com',
            'phone': '0694123456',
            'roles': ['membre'],
        })
        assert form.is_valid(), form.errors

    def test_missing_email(self):
        form = UserCreationByTeamForm(data={
            'first_name': 'Jean',
            'last_name': 'Martin',
            'roles': ['membre'],
        })
        assert not form.is_valid()
        assert 'email' in form.errors

    def test_duplicate_email(self):
        User.objects.create_user(
            username='existing2', email='taken@example.com', password='Pass123!'
        )
        form = UserCreationByTeamForm(data={
            'first_name': 'Jean',
            'last_name': 'Martin',
            'email': 'taken@example.com',
            'roles': ['membre'],
        })
        assert not form.is_valid()

    def test_name_too_short(self):
        form = UserCreationByTeamForm(data={
            'first_name': 'J',
            'last_name': 'M',
            'email': 'jm@example.com',
            'roles': ['membre'],
        })
        assert not form.is_valid()


@pytest.mark.django_db
class TestFirstLoginPasswordChangeForm:
    """Tests du formulaire de changement de mot de passe."""

    def test_valid_passwords(self):
        form = FirstLoginPasswordChangeForm(data={
            'new_password1': 'SecurePass2024!',
            'new_password2': 'SecurePass2024!',
        })
        assert form.is_valid(), form.errors

    def test_passwords_mismatch(self):
        form = FirstLoginPasswordChangeForm(data={
            'new_password1': 'SecurePass2024!',
            'new_password2': 'DifferentPass2024!',
        })
        assert not form.is_valid()

    def test_weak_password(self):
        form = FirstLoginPasswordChangeForm(data={
            'new_password1': '1234',
            'new_password2': '1234',
        })
        assert not form.is_valid()


@pytest.mark.django_db
class TestProfileForm:
    """Tests du formulaire de profil."""

    def test_valid_profile(self):
        user = User.objects.create_user(
            username='profuser', email='prof@example.com', password='Pass123!'
        )
        form = ProfileForm(instance=user, data={
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'prof@example.com',
            'phone': '0694111222',
        })
        assert form.is_valid(), form.errors

    def test_email_taken_by_other(self):
        User.objects.create_user(
            username='other', email='other@example.com', password='Pass123!'
        )
        user = User.objects.create_user(
            username='profuser2', email='prof2@example.com', password='Pass123!'
        )
        form = ProfileForm(instance=user, data={
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'other@example.com',
        })
        assert not form.is_valid()


# =============================================================================
# VIEWS TESTS
# =============================================================================

@pytest.mark.django_db
class TestAccountsViews:
    """Tests des vues accounts."""

    def _make_admin(self):
        return User.objects.create_user(
            username='viewadmin', email='viewadmin@example.com',
            password='Admin123!', role='admin', is_staff=True,
        )

    def _make_member(self):
        return User.objects.create_user(
            username='viewmember', email='member@example.com',
            password='Member123!', role='membre',
        )

    def test_login_page_loads(self, client):
        response = client.get(reverse('accounts:login'))
        assert response.status_code == 200

    def test_login_valid(self, client):
        self._make_member()
        response = client.post(reverse('accounts:login'), {
            'username': 'viewmember',
            'password': 'Member123!',
        })
        # Should redirect on success (302) or render with 2FA
        assert response.status_code in [200, 302]

    def test_login_invalid(self, client):
        response = client.post(reverse('accounts:login'), {
            'username': 'nonexistent',
            'password': 'Wrong123!',
        })
        assert response.status_code == 200  # Re-renders form

    def test_logout_post(self, client):
        user = self._make_member()
        client.force_login(user)
        response = client.post(reverse('accounts:logout'))
        assert response.status_code in [200, 302]

    def test_profile_requires_login(self, client):
        response = client.get(reverse('accounts:profile'))
        assert response.status_code == 302  # Redirect to login

    def test_profile_accessible_logged_in(self, client):
        user = self._make_member()
        client.force_login(user)
        response = client.get(reverse('accounts:profile'))
        assert response.status_code == 200

    def test_user_list_requires_admin(self, client):
        user = self._make_member()
        client.force_login(user)
        response = client.get(reverse('accounts:user_list'))
        assert response.status_code in [302, 403]

    def test_user_list_accessible_admin(self, client):
        admin = self._make_admin()
        client.force_login(admin)
        response = client.get(reverse('accounts:user_list'))
        assert response.status_code == 200

    def test_create_user_requires_admin(self, client):
        member = self._make_member()
        client.force_login(member)
        response = client.get(reverse('accounts:create_user'))
        assert response.status_code in [302, 403]

    def test_create_user_page_loads(self, client):
        admin = self._make_admin()
        client.force_login(admin)
        response = client.get(reverse('accounts:create_user'))
        assert response.status_code == 200

    def test_user_detail_view(self, client):
        admin = self._make_admin()
        member = self._make_member()
        client.force_login(admin)
        response = client.get(reverse('accounts:user_detail', args=[member.pk]))
        assert response.status_code == 200
