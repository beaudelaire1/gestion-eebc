"""
Tests pour le système d'audit logging.

Property 3: Audit Log Creation
Pour toute action sensible (login, logout, modification de données, export, accès refusé),
une entrée AuditLog est créée avec l'utilisateur, le type d'action et le timestamp corrects.

Validates: Requirements 4.5, 8.2, 8.3, 8.4
"""

import pytest
from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from hypothesis import given, strategies as st, settings as hypothesis_settings, HealthCheck

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
        username='testuser',
        password='testpass123',
        first_name='Test',
        last_name='User',
        role='membre'
    )


# =============================================================================
# TESTS UNITAIRES - MODÈLE AUDITLOG
# =============================================================================

class TestAuditLogModel:
    """Tests pour le modèle AuditLog."""
    
    def test_create_audit_log_entry(self, db, admin_user):
        """Test de création d'une entrée d'audit basique."""
        log = AuditLog.log(
            action=AuditLog.Action.LOGIN,
            user=admin_user,
            model_name='accounts.User',
            object_id=admin_user.pk,
            object_repr=str(admin_user)
        )
        
        assert log.pk is not None
        assert log.action == AuditLog.Action.LOGIN
        assert log.user == admin_user
        assert log.model_name == 'accounts.User'
        assert log.object_id == str(admin_user.pk)
    
    def test_audit_log_str_representation(self, db, admin_user):
        """Test de la représentation string de l'AuditLog."""
        log = AuditLog.log(
            action=AuditLog.Action.CREATE,
            user=admin_user,
            model_name='members.Member'
        )
        
        str_repr = str(log)
        assert admin_user.username in str_repr
        assert 'Création' in str_repr
    
    def test_audit_log_anonymous_user(self, db):
        """Test d'audit pour un utilisateur anonyme."""
        log = AuditLog.log(
            action=AuditLog.Action.LOGIN_FAILED,
            user=None,
            extra_data={'attempted_username': 'unknown'}
        )
        
        assert log.user is None
        str_repr = str(log)
        assert 'Anonyme' in str_repr
    
    def test_audit_log_from_request(self, db, admin_user, request_factory):
        """Test de création d'audit depuis une requête HTTP."""
        request = request_factory.get('/test/')
        request.user = admin_user
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 Test'
        
        log = AuditLog.log_from_request(
            request=request,
            action=AuditLog.Action.VIEW,
            model_name='members.Member'
        )
        
        assert log.user == admin_user
        assert log.ip_address == '192.168.1.1'
        assert 'Mozilla' in log.user_agent
        assert log.path == '/test/'
    
    def test_get_client_ip_direct(self, request_factory):
        """Test d'extraction de l'IP directe."""
        request = request_factory.get('/')
        request.META['REMOTE_ADDR'] = '10.0.0.1'
        
        ip = AuditLog.get_client_ip(request)
        assert ip == '10.0.0.1'
    
    def test_get_client_ip_forwarded(self, request_factory):
        """Test d'extraction de l'IP via X-Forwarded-For."""
        request = request_factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.195, 70.41.3.18'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        ip = AuditLog.get_client_ip(request)
        assert ip == '203.0.113.195'


# =============================================================================
# TESTS - LOGGING DES CONNEXIONS/DÉCONNEXIONS (Requirement 8.2)
# =============================================================================

class TestLoginLogoutAudit:
    """Tests pour le logging des connexions/déconnexions."""
    
    def test_login_creates_audit_log(self, db, client, test_user):
        """
        Property 3: Une connexion réussie crée une entrée AuditLog.
        Validates: Requirement 8.2
        """
        # Effacer les logs existants
        AuditLog.objects.all().delete()
        
        # Se connecter
        response = client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Vérifier qu'un log de connexion a été créé
        login_logs = AuditLog.objects.filter(
            action=AuditLog.Action.LOGIN,
            user=test_user
        )
        
        assert login_logs.exists(), "Un log de connexion devrait être créé"
        log = login_logs.first()
        assert log.model_name == 'accounts.User'
        assert log.object_id == str(test_user.pk)
    
    def test_logout_creates_audit_log(self, db, client, test_user):
        """
        Property 3: Une déconnexion crée une entrée AuditLog.
        Validates: Requirement 8.2
        """
        # Se connecter d'abord
        client.force_login(test_user)
        
        # Effacer les logs existants
        AuditLog.objects.all().delete()
        
        # Se déconnecter
        response = client.post(reverse('accounts:logout'))
        
        # Vérifier qu'un log de déconnexion a été créé
        logout_logs = AuditLog.objects.filter(
            action=AuditLog.Action.LOGOUT,
            user=test_user
        )
        
        assert logout_logs.exists(), "Un log de déconnexion devrait être créé"
    
    def test_failed_login_creates_audit_log(self, db, client, test_user):
        """
        Property 3: Une tentative de connexion échouée crée une entrée AuditLog.
        Validates: Requirement 8.2
        """
        # Effacer les logs existants
        AuditLog.objects.all().delete()
        
        # Tenter une connexion avec un mauvais mot de passe (utilisateur existant)
        response = client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        # Vérifier qu'un log d'échec a été créé
        failed_logs = AuditLog.objects.filter(
            action=AuditLog.Action.LOGIN_FAILED
        )
        
        assert failed_logs.exists(), "Un log d'échec de connexion devrait être créé"


# =============================================================================
# TESTS - LOGGING DES ACCÈS REFUSÉS (Requirement 8.4)
# =============================================================================

class TestAccessDeniedAudit:
    """Tests pour le logging des accès refusés."""
    
    def test_access_denied_creates_audit_log(self, db, client, membre_user):
        """
        Property 3: Un accès refusé crée une entrée AuditLog.
        Validates: Requirement 8.4
        """
        # Se connecter avec un utilisateur membre
        client.force_login(membre_user)
        
        # Effacer les logs existants
        AuditLog.objects.all().delete()
        
        # Tenter d'accéder à une vue finance (réservée admin/finance)
        response = client.get(reverse('finance:dashboard'))
        
        # Vérifier qu'un log d'accès refusé a été créé
        denied_logs = AuditLog.objects.filter(
            action=AuditLog.Action.ACCESS_DENIED,
            user=membre_user
        )
        
        assert denied_logs.exists(), "Un log d'accès refusé devrait être créé"
        log = denied_logs.first()
        assert 'required_roles' in log.extra_data
        assert log.extra_data.get('user_role') == 'membre'


# =============================================================================
# TESTS - LOGGING DES EXPORTS (Requirement 4.5)
# =============================================================================

class TestExportAudit:
    """Tests pour le logging des exports."""
    
    def test_export_creates_audit_log(self, db, client, admin_user):
        """
        Property 3: Un export crée une entrée AuditLog.
        Validates: Requirement 4.5
        """
        # Se connecter en tant qu'admin
        client.force_login(admin_user)
        
        # Effacer les logs existants
        AuditLog.objects.all().delete()
        
        # Effectuer un export (membres)
        response = client.get(reverse('exports:members_excel'))
        
        # Vérifier qu'un log d'export a été créé
        export_logs = AuditLog.objects.filter(
            action=AuditLog.Action.EXPORT,
            user=admin_user
        )
        
        assert export_logs.exists(), "Un log d'export devrait être créé"
        log = export_logs.first()
        assert log.extra_data.get('export_type') == 'members'
        assert log.extra_data.get('success') is True
    
    def test_export_denied_creates_audit_log(self, db, client, membre_user):
        """
        Property 3: Un export refusé crée une entrée AuditLog.
        Validates: Requirements 4.5, 8.4
        """
        # Se connecter avec un utilisateur membre
        client.force_login(membre_user)
        
        # Effacer les logs existants
        AuditLog.objects.all().delete()
        
        # Tenter un export (devrait être refusé)
        response = client.get(reverse('exports:members_excel'))
        
        # Vérifier qu'un log d'accès refusé a été créé
        denied_logs = AuditLog.objects.filter(
            action=AuditLog.Action.ACCESS_DENIED,
            user=membre_user
        )
        
        assert denied_logs.exists(), "Un log d'accès refusé devrait être créé pour l'export"


# =============================================================================
# PROPERTY-BASED TESTS
# =============================================================================

class TestAuditLogProperties:
    """Tests property-based pour l'audit logging."""
    
    @given(
        action=st.sampled_from([
            AuditLog.Action.LOGIN,
            AuditLog.Action.LOGOUT,
            AuditLog.Action.CREATE,
            AuditLog.Action.UPDATE,
            AuditLog.Action.DELETE,
            AuditLog.Action.EXPORT,
            AuditLog.Action.ACCESS_DENIED,
        ]),
        model_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        object_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('N',))),
    )
    @hypothesis_settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
    def test_audit_log_creation_preserves_data(self, db, action, model_name, object_id):
        """
        Property 3: Pour toute action, les données sont préservées dans l'AuditLog.
        
        *For any* action type, model name, and object ID, creating an AuditLog entry
        should preserve all provided data accurately.
        
        Validates: Requirements 4.5, 8.2, 8.3, 8.4
        """
        log = AuditLog.log(
            action=action,
            model_name=model_name,
            object_id=object_id
        )
        
        # Vérifier que les données sont préservées
        assert log.action == action
        assert log.model_name == model_name
        assert log.object_id == object_id
        assert log.timestamp is not None
        
        # Nettoyer
        log.delete()
    
    @given(
        ip=st.ip_addresses(v=4).map(str),
        user_agent=st.text(min_size=0, max_size=100)
    )
    @hypothesis_settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_audit_log_preserves_request_context(self, db, request_factory, ip, user_agent):
        """
        Property 3: Le contexte de la requête est préservé dans l'AuditLog.
        
        *For any* IP address and user agent, the request context should be
        accurately recorded in the AuditLog entry.
        
        Validates: Requirements 8.2, 8.3, 8.4
        """
        request = request_factory.get('/test/')
        request.user = None
        request.META['REMOTE_ADDR'] = ip
        request.META['HTTP_USER_AGENT'] = user_agent
        
        # Simuler un utilisateur non authentifié
        class AnonymousUser:
            is_authenticated = False
        request.user = AnonymousUser()
        
        log = AuditLog.log_from_request(
            request=request,
            action=AuditLog.Action.LOGIN_FAILED
        )
        
        # Vérifier que le contexte est préservé
        assert log.ip_address == ip
        assert log.user_agent == user_agent[:500]  # Tronqué à 500 caractères
        assert log.path == '/test/'
        
        # Nettoyer
        log.delete()
