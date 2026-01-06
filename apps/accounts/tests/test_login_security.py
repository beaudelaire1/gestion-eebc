"""
Tests pour le flux de login sécurisé.

Property 4: Login Rate Limiting
Property 5: Secure Password Change Flow

Validates: Requirements 5.1, 5.2, 5.3
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from hypothesis import given, strategies as st, settings, HealthCheck

from apps.accounts.services import AuthenticationService
from apps.accounts.models import PasswordChangeToken

User = get_user_model()


class TestRateLimiting:
    """
    Property 4: Login Rate Limiting
    
    *For any* IP address, after 5 failed login attempts within 1 minute,
    subsequent login attempts are blocked for 15 minutes.
    
    **Validates: Requirements 5.2, 9.1**
    """
    
    @pytest.fixture
    def test_user(self, db):
        """Crée un utilisateur de test."""
        return User.objects.create_user(
            username='rate_limit_test',
            password='correct_password123',
            first_name='Rate',
            last_name='Limit'
        )
    
    def test_successful_login_resets_failed_attempts(self, db, test_user):
        """
        Feature: security-audit-fixes, Property 4: Login Rate Limiting
        Un login réussi réinitialise le compteur de tentatives échouées.
        """
        # Simuler quelques tentatives échouées
        test_user.failed_login_attempts = 3
        test_user.save()
        
        # Login réussi
        user, error = AuthenticationService.authenticate_user(
            username='rate_limit_test',
            password='correct_password123'
        )
        
        assert user is not None
        assert error == ""
        
        # Recharger l'utilisateur
        test_user.refresh_from_db()
        assert test_user.failed_login_attempts == 0
        assert test_user.locked_until is None
    
    def test_failed_login_increments_counter(self, db, test_user):
        """
        Feature: security-audit-fixes, Property 4: Login Rate Limiting
        Un login échoué incrémente le compteur de tentatives.
        """
        initial_attempts = test_user.failed_login_attempts
        
        user, error = AuthenticationService.authenticate_user(
            username='rate_limit_test',
            password='wrong_password'
        )
        
        assert user is None
        assert "incorrect" in error.lower() or "tentative" in error.lower()
        
        test_user.refresh_from_db()
        assert test_user.failed_login_attempts == initial_attempts + 1
    
    def test_account_locked_after_max_attempts(self, db, test_user):
        """
        Feature: security-audit-fixes, Property 4: Login Rate Limiting
        Le compte est verrouillé après 5 tentatives échouées.
        """
        # Simuler 4 tentatives échouées
        test_user.failed_login_attempts = 4
        test_user.save()
        
        # 5ème tentative échouée
        user, error = AuthenticationService.authenticate_user(
            username='rate_limit_test',
            password='wrong_password'
        )
        
        assert user is None
        
        test_user.refresh_from_db()
        assert test_user.failed_login_attempts == 5
        assert test_user.locked_until is not None
        assert test_user.is_locked()
    
    def test_locked_account_blocks_login(self, db, test_user):
        """
        Feature: security-audit-fixes, Property 4: Login Rate Limiting
        Un compte verrouillé bloque les tentatives de connexion.
        """
        # Verrouiller le compte
        test_user.locked_until = timezone.now() + timedelta(minutes=15)
        test_user.save()
        
        # Tenter de se connecter avec le bon mot de passe
        user, error = AuthenticationService.authenticate_user(
            username='rate_limit_test',
            password='correct_password123'
        )
        
        assert user is None
        assert "verrouillé" in error.lower() or "locked" in error.lower()
    
    def test_lock_expires_after_timeout(self, db, test_user):
        """
        Feature: security-audit-fixes, Property 4: Login Rate Limiting
        Le verrouillage expire après le délai configuré.
        """
        # Verrouiller le compte dans le passé
        test_user.locked_until = timezone.now() - timedelta(minutes=1)
        test_user.failed_login_attempts = 5
        test_user.save()
        
        # Le compte ne devrait plus être verrouillé
        assert not test_user.is_locked()
        
        # Le login devrait fonctionner
        user, error = AuthenticationService.authenticate_user(
            username='rate_limit_test',
            password='correct_password123'
        )
        
        assert user is not None
        assert error == ""
    
    @given(attempts=st.integers(min_value=1, max_value=10))
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rate_limiting_property(self, attempts, db):
        """
        Feature: security-audit-fixes, Property 4: Login Rate Limiting
        
        Property-based test: Pour tout nombre de tentatives échouées,
        le compte est verrouillé si et seulement si attempts >= 5.
        
        **Validates: Requirements 5.2**
        """
        # Créer un utilisateur frais pour chaque test
        user = User.objects.create_user(
            username=f'pbt_user_{attempts}_{timezone.now().timestamp()}',
            password='test_password123'
        )
        
        # Simuler les tentatives échouées
        for _ in range(attempts):
            AuthenticationService.authenticate_user(
                username=user.username,
                password='wrong_password'
            )
        
        user.refresh_from_db()
        
        # Vérifier la propriété
        if attempts >= 5:
            assert user.is_locked(), f"Account should be locked after {attempts} attempts"
        else:
            assert not user.is_locked(), f"Account should not be locked after {attempts} attempts"


class TestSecurePasswordChangeFlow:
    """
    Property 5: Secure Password Change Flow
    
    *For any* user requiring password change, the system uses a signed token
    (not plaintext password in session) and the token is valid only once
    and expires after a configured time.
    
    **Validates: Requirements 5.1, 5.3**
    """
    
    @pytest.fixture
    def must_change_user(self, db):
        """Crée un utilisateur qui doit changer son mot de passe."""
        return User.objects.create_user(
            username='must_change_test',
            password='temp_password123',
            first_name='Must',
            last_name='Change',
            must_change_password=True
        )
    
    def test_generate_token_creates_valid_token(self, db, must_change_user):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        La génération de token crée un token valide.
        """
        token = AuthenticationService.generate_password_change_token(must_change_user)
        
        assert token is not None
        assert len(token) > 0
        
        # Le token doit être vérifiable
        user = AuthenticationService.verify_password_change_token(token)
        assert user == must_change_user
    
    def test_token_is_unique(self, db, must_change_user):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        Chaque token généré est unique.
        """
        token1 = AuthenticationService.generate_password_change_token(must_change_user)
        token2 = AuthenticationService.generate_password_change_token(must_change_user)
        
        assert token1 != token2
    
    def test_old_tokens_invalidated_on_new_generation(self, db, must_change_user):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        Les anciens tokens sont invalidés quand un nouveau est généré.
        """
        token1 = AuthenticationService.generate_password_change_token(must_change_user)
        token2 = AuthenticationService.generate_password_change_token(must_change_user)
        
        # Le premier token ne devrait plus être valide
        user1 = AuthenticationService.verify_password_change_token(token1)
        user2 = AuthenticationService.verify_password_change_token(token2)
        
        assert user1 is None  # Ancien token invalidé
        assert user2 == must_change_user  # Nouveau token valide
    
    def test_token_consumed_only_once(self, db, must_change_user):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        Un token ne peut être consommé qu'une seule fois.
        """
        token = AuthenticationService.generate_password_change_token(must_change_user)
        
        # Première consommation
        user1 = AuthenticationService.consume_password_change_token(token)
        assert user1 == must_change_user
        
        # Deuxième tentative de consommation
        user2 = AuthenticationService.consume_password_change_token(token)
        assert user2 is None
    
    def test_expired_token_is_invalid(self, db, must_change_user):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        Un token expiré n'est pas valide.
        """
        # Créer un token expiré directement en base
        raw_token = PasswordChangeToken.generate_token()
        expired_token = PasswordChangeToken.objects.create(
            user=must_change_user,
            token=raw_token,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        assert not expired_token.is_valid()
    
    def test_used_token_is_invalid(self, db, must_change_user):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        Un token déjà utilisé n'est pas valide.
        """
        raw_token = PasswordChangeToken.generate_token()
        used_token = PasswordChangeToken.objects.create(
            user=must_change_user,
            token=raw_token,
            expires_at=timezone.now() + timedelta(hours=1),
            used=True
        )
        
        assert not used_token.is_valid()
    
    def test_invalid_signed_token_returns_none(self, db):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        Un token signé invalide retourne None.
        """
        user = AuthenticationService.verify_password_change_token('invalid_token')
        assert user is None
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=10)
    def test_random_tokens_are_invalid(self, random_token):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        
        Property-based test: Pour toute chaîne aléatoire,
        la vérification du token retourne None.
        
        **Validates: Requirements 5.3**
        """
        user = AuthenticationService.verify_password_change_token(random_token)
        assert user is None


class TestLoginViewIntegration:
    """Tests d'intégration pour la vue de login."""
    
    @pytest.fixture
    def normal_user(self, db):
        """Crée un utilisateur normal."""
        return User.objects.create_user(
            username='normal_user',
            password='test_password123',
            first_name='Normal',
            last_name='User'
        )
    
    @pytest.fixture
    def must_change_user(self, db):
        """Crée un utilisateur qui doit changer son mot de passe."""
        return User.objects.create_user(
            username='must_change_user',
            password='temp_password123',
            first_name='Must',
            last_name='Change',
            must_change_password=True
        )
    
    def test_successful_login_redirects_to_dashboard(self, client, normal_user):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        Un login réussi redirige vers le dashboard.
        """
        login_url = reverse('accounts:login')
        response = client.post(login_url, {
            'username': 'normal_user',
            'password': 'test_password123'
        })
        
        assert response.status_code == 302
        # Vérifier que la redirection est vers le dashboard ou l'app
        assert 'dashboard' in response.url or '/app' in response.url or response.url == '/'
    
    def test_must_change_password_redirects_with_token(self, client, must_change_user):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        Un utilisateur devant changer son mot de passe est redirigé avec un token.
        """
        login_url = reverse('accounts:login')
        response = client.post(login_url, {
            'username': 'must_change_user',
            'password': 'temp_password123'
        })
        
        assert response.status_code == 302
        assert 'first-login-password-change' in response.url or 'first_login_password_change' in response.url
        assert 'token=' in response.url
    
    def test_failed_login_shows_error(self, client, normal_user):
        """
        Feature: security-audit-fixes, Property 4: Login Rate Limiting
        Un login échoué affiche un message d'erreur.
        """
        login_url = reverse('accounts:login')
        response = client.post(login_url, {
            'username': 'normal_user',
            'password': 'wrong_password'
        }, follow=True)
        
        # Vérifier que le message d'erreur est présent
        messages = list(response.context.get('messages', []))
        assert len(messages) > 0
    
    def test_locked_account_shows_error(self, client, normal_user):
        """
        Feature: security-audit-fixes, Property 4: Login Rate Limiting
        Un compte verrouillé affiche un message d'erreur approprié.
        """
        # Verrouiller le compte
        normal_user.locked_until = timezone.now() + timedelta(minutes=15)
        normal_user.save()
        
        login_url = reverse('accounts:login')
        response = client.post(login_url, {
            'username': 'normal_user',
            'password': 'test_password123'
        }, follow=True)
        
        messages = list(response.context.get('messages', []))
        assert len(messages) > 0
        # Vérifier que le message mentionne le verrouillage
        message_text = str(messages[0]).lower()
        assert 'verrouillé' in message_text or 'minute' in message_text


class TestPasswordChangeTokenModel:
    """Tests pour le modèle PasswordChangeToken."""
    
    @pytest.fixture
    def test_user(self, db):
        """Crée un utilisateur de test."""
        return User.objects.create_user(
            username='token_test_user',
            password='test123'
        )
    
    def test_generate_token_is_secure(self, db, test_user):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        Le token généré est suffisamment long et aléatoire.
        """
        token = PasswordChangeToken.generate_token()
        
        # Le token doit être suffisamment long (au moins 32 caractères)
        assert len(token) >= 32
    
    def test_is_valid_returns_true_for_valid_token(self, db, test_user):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        is_valid() retourne True pour un token valide.
        """
        token = PasswordChangeToken.objects.create(
            user=test_user,
            token=PasswordChangeToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        assert token.is_valid()
    
    def test_mark_as_used_invalidates_token(self, db, test_user):
        """
        Feature: security-audit-fixes, Property 5: Secure Password Change Flow
        mark_as_used() invalide le token.
        """
        token = PasswordChangeToken.objects.create(
            user=test_user,
            token=PasswordChangeToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        assert token.is_valid()
        
        token.mark_as_used()
        
        assert not token.is_valid()
        assert token.used
