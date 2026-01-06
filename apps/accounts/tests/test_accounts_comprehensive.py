"""
Tests unitaires complets pour le module accounts.

Couvre:
- Login et authentification
- Création d'utilisateurs
- Système de permissions
- Flux de changement de mot de passe
- Gestion des rôles

Requirements: 24.1
"""

import pytest
from django.contrib.auth import get_user_model, authenticate
from django.urls import reverse
from django.test import Client
from django.contrib.messages import get_messages
from django.utils import timezone
from datetime import timedelta

from apps.accounts.services import AuthenticationService
from apps.accounts.models import PasswordChangeToken
from apps.core.permissions import has_role, get_user_permissions

User = get_user_model()


class TestUserModel:
    """Tests pour le modèle User étendu."""
    
    def test_user_creation_with_role(self, db):
        """Un utilisateur peut être créé avec un rôle."""
        user = User.objects.create_user(
            username='test_user',
            password='test123',
            role='finance'
        )
        
        assert user.username == 'test_user'
        assert user.role == 'finance'
        assert user.check_password('test123')
    
    def test_user_default_values(self, db):
        """Les valeurs par défaut sont correctes."""
        user = User.objects.create_user(
            username='default_user',
            password='test123'
        )
        
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        assert user.must_change_password is False
        assert user.created_by_team is False
    
    def test_is_locked_method(self, db):
        """La méthode is_locked() fonctionne correctement."""
        user = User.objects.create_user(
            username='locked_user',
            password='test123'
        )
        
        # Utilisateur non verrouillé
        assert not user.is_locked()
        
        # Verrouiller dans le futur
        user.locked_until = timezone.now() + timedelta(minutes=15)
        assert user.is_locked()
        
        # Verrouillage expiré
        user.locked_until = timezone.now() - timedelta(minutes=1)
        assert not user.is_locked()
    
    def test_superuser_has_admin_role(self, db):
        """Un superuser a automatiquement le rôle admin."""
        superuser = User.objects.create_superuser(
            username='super',
            password='super123'
        )
        
        assert superuser.is_superuser
        assert superuser.role == 'admin'


class TestAuthentication:
    """Tests pour l'authentification."""
    
    @pytest.fixture
    def active_user(self, db):
        """Utilisateur actif normal."""
        return User.objects.create_user(
            username='active_user',
            password='active123',
            role='membre'
        )
    
    @pytest.fixture
    def inactive_user(self, db):
        """Utilisateur devant changer son mot de passe."""
        return User.objects.create_user(
            username='inactive_user',
            password='temp123',
            must_change_password=True,
            role='membre'
        )
    
    def test_authenticate_active_user(self, active_user):
        """L'authentification fonctionne pour un utilisateur actif."""
        user = authenticate(username='active_user', password='active123')
        assert user == active_user
    
    def test_authenticate_inactive_user(self, inactive_user):
        """L'authentification fonctionne pour un utilisateur inactif."""
        user = authenticate(username='inactive_user', password='temp123')
        assert user == inactive_user
    
    def test_authenticate_wrong_password(self, active_user):
        """L'authentification échoue avec un mauvais mot de passe."""
        user = authenticate(username='active_user', password='wrong')
        assert user is None
    
    def test_authenticate_nonexistent_user(self, db):
        """L'authentification échoue pour un utilisateur inexistant."""
        user = authenticate(username='nonexistent', password='any')
        assert user is None


class TestLoginView:
    """Tests pour la vue de login."""
    
    @pytest.fixture
    def client(self):
        """Client de test."""
        return Client()
    
    @pytest.fixture
    def normal_user(self, db):
        """Utilisateur normal."""
        return User.objects.create_user(
            username='normal',
            password='normal123',
            role='membre'
        )
    
    @pytest.fixture
    def must_change_user(self, db):
        """Utilisateur devant changer son mot de passe."""
        return User.objects.create_user(
            username='mustchange',
            password='temp123',
            must_change_password=True,
            role='membre'
        )
    
    def test_login_page_accessible(self, client):
        """La page de login est accessible."""
        response = client.get(reverse('accounts:login'))
        assert response.status_code == 200
    
    def test_successful_login_normal_user(self, client, normal_user):
        """Login réussi pour un utilisateur normal."""
        response = client.post(reverse('accounts:login'), {
            'username': 'normal',
            'password': 'normal123'
        })
        
        assert response.status_code == 302
        # Vérifier que l'utilisateur est connecté
        assert '_auth_user_id' in client.session
    
    def test_successful_login_must_change_password(self, client, must_change_user):
        """Login réussi pour un utilisateur devant changer son mot de passe."""
        response = client.post(reverse('accounts:login'), {
            'username': 'mustchange',
            'password': 'temp123'
        })
        
        assert response.status_code == 302
        # Doit rediriger vers la page de changement de mot de passe
        assert 'first-login-password-change' in response.url or 'first_login_password_change' in response.url
    
    def test_failed_login_shows_error(self, client, normal_user):
        """Login échoué affiche une erreur."""
        response = client.post(reverse('accounts:login'), {
            'username': 'normal',
            'password': 'wrong'
        }, follow=True)
        
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert any('incorrect' in str(msg).lower() for msg in messages)
    
    def test_locked_user_cannot_login(self, client, normal_user):
        """Un utilisateur verrouillé ne peut pas se connecter."""
        # Verrouiller l'utilisateur
        normal_user.locked_until = timezone.now() + timedelta(minutes=15)
        normal_user.save()
        
        response = client.post(reverse('accounts:login'), {
            'username': 'normal',
            'password': 'normal123'
        }, follow=True)
        
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert any('verrouillé' in str(msg).lower() or 'locked' in str(msg).lower() for msg in messages)


class TestUserCreation:
    """Tests pour la création d'utilisateurs."""
    
    @pytest.fixture
    def admin_user(self, db):
        """Utilisateur admin."""
        return User.objects.create_user(
            username='admin',
            password='admin123',
            role='admin'
        )
    
    def test_create_user_by_team_success(self, admin_user, settings):
        """Création d'utilisateur par équipe réussie."""
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        result = AuthenticationService.create_user_by_team(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            role="membre",
            created_by=admin_user,
            send_email=False
        )
        
        assert result.success
        user = result.data['user']
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.email == "test@example.com"
        assert user.role == "membre"
        assert user.created_by_team
        assert user.must_change_password
    
    def test_username_generation(self, admin_user):
        """La génération de nom d'utilisateur fonctionne."""
        username = AuthenticationService.generate_username("Jean", "Dupont")
        assert username == "je_dupont"
        
        # Test avec accents
        username = AuthenticationService.generate_username("François", "Müller")
        assert username == "fr_muller"
    
    def test_password_generation(self):
        """La génération de mot de passe fonctionne."""
        password = AuthenticationService.generate_password()
        
        assert len(password) >= 12
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%&*" for c in password)


class TestPermissions:
    """Tests pour le système de permissions."""
    
    @pytest.fixture
    def users_by_role(self, db):
        """Crée des utilisateurs pour chaque rôle."""
        users = {}
        roles = ['admin', 'secretariat', 'finance', 'responsable_club', 
                'moniteur', 'responsable_groupe', 'encadrant', 'membre']
        
        for role in roles:
            users[role] = User.objects.create_user(
                username=f'{role}_user',
                password='test123',
                role=role
            )
        
        return users
    
    def test_has_role_function(self, users_by_role):
        """La fonction has_role fonctionne correctement."""
        admin = users_by_role['admin']
        finance = users_by_role['finance']
        membre = users_by_role['membre']
        
        # Admin a tous les rôles
        assert has_role(admin, 'admin')
        assert has_role(admin, 'finance')  # Admin peut tout faire
        
        # Finance a son rôle
        assert has_role(finance, 'finance')
        assert not has_role(finance, 'admin')
        
        # Membre n'a que son rôle
        assert has_role(membre, 'membre')
        assert not has_role(membre, 'finance')
        assert not has_role(membre, 'admin')
    
    def test_superuser_has_all_permissions(self, db):
        """Un superuser a toutes les permissions."""
        superuser = User.objects.create_superuser(
            username='super',
            password='super123'
        )
        
        # Superuser devrait avoir tous les rôles
        assert has_role(superuser, 'admin')
        assert has_role(superuser, 'finance')
        assert has_role(superuser, 'secretariat')
    
    def test_get_user_permissions(self, users_by_role):
        """La fonction get_user_permissions retourne les bonnes permissions."""
        admin = users_by_role['admin']
        finance = users_by_role['finance']
        
        admin_perms = get_user_permissions(admin)
        finance_perms = get_user_permissions(finance)
        
        # Admin devrait avoir accès à tous les modules
        assert admin_perms['modules'] == ['*']
        
        # Finance devrait avoir accès aux modules finance
        assert 'finance' in finance_perms['modules']
        assert 'campaigns' in finance_perms['modules']


class TestPasswordChangeFlow:
    """Tests pour le flux de changement de mot de passe."""
    
    @pytest.fixture
    def must_change_user(self, db):
        """Utilisateur devant changer son mot de passe."""
        return User.objects.create_user(
            username='mustchange',
            password='temp123',
            must_change_password=True
        )
    
    def test_generate_password_change_token(self, must_change_user):
        """Génération de token de changement de mot de passe."""
        token = AuthenticationService.generate_password_change_token(must_change_user)
        
        assert token is not None
        assert len(token) > 0
        
        # Vérifier que le token peut être vérifié
        user = AuthenticationService.verify_password_change_token(token)
        assert user == must_change_user
    
    def test_token_uniqueness(self, must_change_user):
        """Chaque token généré est unique."""
        token1 = AuthenticationService.generate_password_change_token(must_change_user)
        token2 = AuthenticationService.generate_password_change_token(must_change_user)
        
        assert token1 != token2
    
    def test_invalid_token_returns_none(self):
        """Un token invalide retourne None."""
        user = AuthenticationService.verify_password_change_token('invalid_token')
        assert user is None
    
    def test_activate_user_account(self, must_change_user):
        """Activation d'un compte utilisateur."""
        result = AuthenticationService.activate_user_account(
            must_change_user, 
            'NewPassword123!'
        )
        
        assert result.success
        
        # Vérifier que l'utilisateur est activé
        must_change_user.refresh_from_db()
        assert not must_change_user.must_change_password
        assert must_change_user.check_password('NewPassword123!')


class TestPasswordChangeTokenModel:
    """Tests pour le modèle PasswordChangeToken."""
    
    @pytest.fixture
    def test_user(self, db):
        """Utilisateur de test."""
        return User.objects.create_user(
            username='token_user',
            password='test123'
        )
    
    def test_token_generation(self):
        """La génération de token fonctionne."""
        token = PasswordChangeToken.generate_token()
        
        assert len(token) >= 32
        assert isinstance(token, str)
    
    def test_token_validity(self, test_user):
        """La validation de token fonctionne."""
        # Token valide
        valid_token = PasswordChangeToken.objects.create(
            user=test_user,
            token=PasswordChangeToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        assert valid_token.is_valid()
        
        # Token expiré
        expired_token = PasswordChangeToken.objects.create(
            user=test_user,
            token=PasswordChangeToken.generate_token(),
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        assert not expired_token.is_valid()
        
        # Token utilisé
        used_token = PasswordChangeToken.objects.create(
            user=test_user,
            token=PasswordChangeToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=1),
            used=True
        )
        
        assert not used_token.is_valid()
    
    def test_mark_as_used(self, test_user):
        """Marquer un token comme utilisé."""
        token = PasswordChangeToken.objects.create(
            user=test_user,
            token=PasswordChangeToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        assert token.is_valid()
        
        token.mark_as_used()
        
        assert not token.is_valid()
        assert token.used


class TestUserRoles:
    """Tests pour les rôles utilisateur."""
    
    def test_all_roles_exist(self, all_roles):
        """Tous les rôles définis existent."""
        expected_roles = [
            'admin', 'secretariat', 'finance', 'responsable_club',
            'moniteur', 'responsable_groupe', 'encadrant', 'membre'
        ]
        
        assert set(all_roles) == set(expected_roles)
    
    def test_role_hierarchy(self, db):
        """Test de la hiérarchie des rôles."""
        admin = User.objects.create_user(
            username='admin',
            password='test123',
            role='admin'
        )
        
        membre = User.objects.create_user(
            username='membre',
            password='test123',
            role='membre'
        )
        
        # Admin peut tout faire
        assert has_role(admin, 'admin', 'finance', 'secretariat')
        
        # Membre ne peut que son rôle
        assert has_role(membre, 'membre')
        assert not has_role(membre, 'admin')
        assert not has_role(membre, 'finance')