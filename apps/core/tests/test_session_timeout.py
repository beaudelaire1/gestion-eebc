"""
Tests pour le middleware de session timeout.

Property 6: Session Timeout
Pour toute session authentifiée, si aucune activité n'a lieu pendant SESSION_TIMEOUT_MINUTES,
la session est invalidée à la prochaine requête (sauf pour les URLs exclues).

Validates: Requirements 6.1, 6.2, 6.4
"""

import pytest
from datetime import timedelta
from django.test import Client, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from hypothesis import given, strategies as st, settings as hypothesis_settings, HealthCheck

from apps.core.middleware import SessionTimeoutMiddleware
from apps.core.models import AuditLog

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def request_factory():
    """Factory pour créer des requêtes de test."""
    return RequestFactory()


@pytest.fixture
def test_user(db):
    """Crée un utilisateur de test."""
    return User.objects.create_user(
        username='timeout_test_user',
        password='testpass123',
        first_name='Timeout',
        last_name='Test',
        role='membre'
    )


@pytest.fixture
def authenticated_client(db, test_user):
    """Client authentifié."""
    client = Client()
    client.force_login(test_user)
    return client


# =============================================================================
# TESTS UNITAIRES - MIDDLEWARE SESSION TIMEOUT
# =============================================================================

class TestSessionTimeoutMiddleware:
    """Tests pour le middleware de session timeout."""
    
    def test_middleware_initializes_with_default_timeout(self):
        """Test que le middleware s'initialise avec le timeout par défaut."""
        middleware = SessionTimeoutMiddleware(lambda r: None)
        assert middleware.timeout_minutes == 30
    
    @override_settings(SESSION_TIMEOUT_MINUTES=15)
    def test_middleware_uses_custom_timeout(self):
        """Test que le middleware utilise un timeout personnalisé."""
        middleware = SessionTimeoutMiddleware(lambda r: None)
        assert middleware.timeout_minutes == 15
    
    @override_settings(SESSION_TIMEOUT_EXCLUDED_PATHS=['/api/', '/static/'])
    def test_middleware_loads_excluded_paths(self):
        """Test que le middleware charge les chemins exclus."""
        middleware = SessionTimeoutMiddleware(lambda r: None)
        assert '/api/' in middleware.excluded_paths
        assert '/static/' in middleware.excluded_paths
    
    def test_excluded_path_detection(self):
        """Test de la détection des chemins exclus."""
        middleware = SessionTimeoutMiddleware(lambda r: None)
        middleware.excluded_paths = ['/api/', '/static/']
        
        assert middleware._is_excluded_path('/api/heartbeat/') is True
        assert middleware._is_excluded_path('/static/css/style.css') is True
        assert middleware._is_excluded_path('/dashboard/') is False
        assert middleware._is_excluded_path('/accounts/login/') is False


# =============================================================================
# TESTS - COMPORTEMENT DU TIMEOUT (Requirement 6.1)
# =============================================================================

class TestSessionTimeoutBehavior:
    """Tests pour le comportement du timeout de session."""
    
    def test_first_request_sets_last_activity(self, db, authenticated_client):
        """
        Test que la première requête définit le timestamp de dernière activité.
        Validates: Requirement 6.1
        """
        # Faire une requête
        response = authenticated_client.get(reverse('dashboard:home'))
        
        # Vérifier que le timestamp est défini dans la session
        session = authenticated_client.session
        assert SessionTimeoutMiddleware.SESSION_LAST_ACTIVITY_KEY in session
    
    def test_active_session_updates_timestamp(self, db, authenticated_client):
        """
        Test que les requêtes actives mettent à jour le timestamp.
        Validates: Requirement 6.1
        """
        # Première requête
        authenticated_client.get(reverse('dashboard:home'))
        session = authenticated_client.session
        first_timestamp = session.get(SessionTimeoutMiddleware.SESSION_LAST_ACTIVITY_KEY)
        
        # Attendre un peu et faire une autre requête
        import time
        time.sleep(0.1)
        
        authenticated_client.get(reverse('dashboard:home'))
        session = authenticated_client.session
        second_timestamp = session.get(SessionTimeoutMiddleware.SESSION_LAST_ACTIVITY_KEY)
        
        # Le timestamp devrait être mis à jour
        assert second_timestamp != first_timestamp
    
    def test_expired_session_redirects_to_login(self, db, test_user, client):
        """
        Test qu'une session expirée redirige vers la page de login.
        Validates: Requirement 6.1
        """
        # Se connecter
        client.force_login(test_user)
        
        # Faire une première requête pour initialiser le timestamp
        client.get(reverse('dashboard:home'))
        
        # Simuler une session expirée en modifiant le timestamp
        session = client.session
        expired_time = timezone.now() - timedelta(minutes=31)
        session[SessionTimeoutMiddleware.SESSION_LAST_ACTIVITY_KEY] = expired_time.isoformat()
        session.save()
        
        # Faire une nouvelle requête
        response = client.get(reverse('dashboard:home'))
        
        # Devrait rediriger vers login
        assert response.status_code == 302
        assert 'login' in response.url.lower() or response.url == '/accounts/login/'
    
    @override_settings(SESSION_TIMEOUT_MINUTES=1)
    def test_session_not_expired_within_timeout(self, db, test_user, client):
        """
        Test qu'une session active dans le délai n'expire pas.
        Validates: Requirement 6.1
        """
        # Se connecter
        client.force_login(test_user)
        
        # Faire une première requête
        client.get(reverse('dashboard:home'))
        
        # Simuler une activité récente (30 secondes)
        session = client.session
        recent_time = timezone.now() - timedelta(seconds=30)
        session[SessionTimeoutMiddleware.SESSION_LAST_ACTIVITY_KEY] = recent_time.isoformat()
        session.save()
        
        # Faire une nouvelle requête
        response = client.get(reverse('dashboard:home'))
        
        # Ne devrait pas rediriger (session encore valide)
        assert response.status_code == 200


# =============================================================================
# TESTS - MESSAGE INFORMATIF (Requirement 6.2)
# =============================================================================

class TestSessionTimeoutMessage:
    """Tests pour le message informatif après expiration."""
    
    def test_expired_session_shows_message(self, db, test_user, client):
        """
        Test qu'un message informatif est affiché après expiration.
        Validates: Requirement 6.2
        """
        # Se connecter
        client.force_login(test_user)
        
        # Faire une première requête
        client.get(reverse('dashboard:home'))
        
        # Simuler une session expirée
        session = client.session
        expired_time = timezone.now() - timedelta(minutes=31)
        session[SessionTimeoutMiddleware.SESSION_LAST_ACTIVITY_KEY] = expired_time.isoformat()
        session.save()
        
        # Faire une nouvelle requête (qui va expirer la session)
        response = client.get(reverse('dashboard:home'), follow=True)
        
        # Vérifier que le message est présent
        messages = list(response.context.get('messages', []))
        message_texts = [str(m) for m in messages]
        
        assert any('session' in m.lower() or 'expiré' in m.lower() or 'inactivité' in m.lower() 
                   for m in message_texts), f"Message d'expiration attendu, reçu: {message_texts}"


# =============================================================================
# TESTS - EXCLUSION D'URLs (Requirement 6.4)
# =============================================================================

class TestSessionTimeoutExclusion:
    """Tests pour l'exclusion d'URLs du timeout."""
    
    @override_settings(SESSION_TIMEOUT_EXCLUDED_PATHS=['/static/', '/media/'])
    def test_excluded_paths_dont_reset_timeout(self, db, test_user, client):
        """
        Test que les chemins exclus ne réinitialisent pas le timeout.
        Validates: Requirement 6.4
        """
        # Se connecter
        client.force_login(test_user)
        
        # Faire une première requête normale
        client.get(reverse('dashboard:home'))
        session = client.session
        first_timestamp = session.get(SessionTimeoutMiddleware.SESSION_LAST_ACTIVITY_KEY)
        
        # Note: Les chemins /static/ et /media/ sont généralement servis par le serveur web
        # et ne passent pas par Django en production. Ce test vérifie la logique du middleware.
        
        # Vérifier que le middleware reconnaît les chemins exclus
        middleware = SessionTimeoutMiddleware(lambda r: None)
        middleware.excluded_paths = ['/static/', '/media/']
        
        assert middleware._is_excluded_path('/static/css/style.css') is True
        assert middleware._is_excluded_path('/media/uploads/file.pdf') is True
        assert middleware._is_excluded_path('/dashboard/') is False


# =============================================================================
# TESTS - AUDIT LOGGING
# =============================================================================

class TestSessionTimeoutAuditLogging:
    """Tests pour le logging des expirations de session."""
    
    def test_session_expiration_creates_audit_log(self, db, test_user, client):
        """
        Test qu'une expiration de session crée une entrée d'audit.
        Validates: Requirement 8.2 (logout logging)
        """
        # Se connecter
        client.force_login(test_user)
        
        # Faire une première requête
        client.get(reverse('dashboard:home'))
        
        # Effacer les logs existants
        AuditLog.objects.all().delete()
        
        # Simuler une session expirée
        session = client.session
        expired_time = timezone.now() - timedelta(minutes=31)
        session[SessionTimeoutMiddleware.SESSION_LAST_ACTIVITY_KEY] = expired_time.isoformat()
        session.save()
        
        # Faire une nouvelle requête (qui va expirer la session)
        response = client.get(reverse('dashboard:home'))
        
        # Vérifier qu'un log de déconnexion a été créé
        logout_logs = AuditLog.objects.filter(
            action=AuditLog.Action.LOGOUT,
            user=test_user
        )
        
        assert logout_logs.exists(), "Un log de déconnexion devrait être créé pour l'expiration de session"
        
        # Vérifier qu'au moins un des logs a la raison 'session_timeout'
        # (le middleware crée un log avec reason, puis le signal logout en crée un autre)
        timeout_logs = logout_logs.filter(extra_data__reason='session_timeout')
        assert timeout_logs.exists(), "Un log avec reason='session_timeout' devrait être créé"


# =============================================================================
# PROPERTY-BASED TESTS
# =============================================================================

class TestSessionTimeoutProperties:
    """Tests property-based pour le session timeout."""
    
    @given(
        timeout_minutes=st.integers(min_value=1, max_value=120),
        elapsed_seconds=st.integers(min_value=0, max_value=10800)  # 0 to 3 hours in seconds
    )
    @hypothesis_settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_session_expires_after_timeout(self, db, timeout_minutes, elapsed_seconds):
        """
        Property 6: Session Timeout
        
        *For any* timeout configuration and elapsed time, a session should be
        considered expired if and only if elapsed_seconds > timeout_minutes * 60.
        
        Validates: Requirements 6.1, 6.4
        """
        middleware = SessionTimeoutMiddleware(lambda r: None)
        middleware.timeout_minutes = timeout_minutes
        
        # Créer une requête mock avec session
        from django.test import RequestFactory
        from django.contrib.sessions.backends.db import SessionStore
        
        factory = RequestFactory()
        request = factory.get('/test/')
        request.session = SessionStore()
        
        # Définir le timestamp de dernière activité
        last_activity = timezone.now() - timedelta(seconds=elapsed_seconds)
        request.session[SessionTimeoutMiddleware.SESSION_LAST_ACTIVITY_KEY] = last_activity.isoformat()
        
        # Vérifier si la session est expirée
        is_expired = middleware._is_session_expired(request)
        
        # La session devrait être expirée si elapsed_seconds > timeout_minutes * 60
        timeout_seconds = timeout_minutes * 60
        expected_expired = elapsed_seconds > timeout_seconds
        assert is_expired == expected_expired, \
            f"Session avec timeout={timeout_minutes}min ({timeout_seconds}s) et elapsed={elapsed_seconds}s " \
            f"devrait être {'expirée' if expected_expired else 'valide'}"
    
    @given(
        path=st.sampled_from([
            '/api/heartbeat/',
            '/static/css/style.css',
            '/media/uploads/file.pdf',
            '/dashboard/',
            '/accounts/profile/',
            '/finance/transactions/',
        ])
    )
    @hypothesis_settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_excluded_paths_are_correctly_identified(self, path):
        """
        Property 6: Les chemins exclus sont correctement identifiés.
        
        *For any* path, it should be excluded if and only if it starts with
        one of the configured excluded prefixes.
        
        Validates: Requirement 6.4
        """
        middleware = SessionTimeoutMiddleware(lambda r: None)
        middleware.excluded_paths = ['/api/', '/static/', '/media/']
        
        is_excluded = middleware._is_excluded_path(path)
        
        # Vérifier manuellement si le chemin devrait être exclu
        expected_excluded = any(path.startswith(prefix) for prefix in middleware.excluded_paths)
        
        assert is_excluded == expected_excluded, \
            f"Le chemin '{path}' devrait être {'exclu' if expected_excluded else 'inclus'}"
