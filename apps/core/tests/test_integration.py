"""
Tests d'intégration pour les flux critiques.

Couvre:
- Flux login → dashboard
- Flux de changement de mot de passe
- Navigation entre modules avec permissions
- Flux d'export avec audit

Requirements: 24.3
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.utils import timezone
from datetime import timedelta

from apps.accounts.services import AuthenticationService
from apps.core.models import AuditLog
from apps.finance.models import FinancialTransaction
from decimal import Decimal

User = get_user_model()


class TestLoginToDashboardFlow:
    """
    Tests d'intégration pour le flux login → dashboard.
    
    **Validates: Requirements 24.3**
    """
    
    @pytest.fixture
    def client(self):
        """Client de test."""
        return Client()
    
    @pytest.fixture
    def normal_user(self, db):
        """Utilisateur normal actif."""
        return User.objects.create_user(
            username='normal_integration',
            password='integration123',
            first_name='Normal',
            last_name='User',
            role='membre'
        )
    
    @pytest.fixture
    def admin_user(self, db):
        """Utilisateur admin."""
        return User.objects.create_user(
            username='admin_integration',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
    
    @pytest.fixture
    def finance_user(self, db):
        """Utilisateur finance."""
        return User.objects.create_user(
            username='finance_integration',
            password='finance123',
            first_name='Finance',
            last_name='User',
            role='finance'
        )
    
    @pytest.fixture
    def must_change_user(self, db):
        """Utilisateur devant changer son mot de passe."""
        return User.objects.create_user(
            username='mustchange_integration',
            password='temp123',
            first_name='Must',
            last_name='Change',
            role='membre',
            must_change_password=True
        )
    
    def test_successful_login_to_dashboard_flow(self, client, normal_user):
        """
        Flux complet: login réussi → redirection dashboard → accès dashboard.
        
        **Validates: Requirements 24.3**
        """
        # 1. Accéder à la page de login
        login_response = client.get(reverse('accounts:login'))
        assert login_response.status_code == 200
        
        # 2. Soumettre les identifiants corrects
        login_post_response = client.post(reverse('accounts:login'), {
            'username': 'normal_integration',
            'password': 'integration123'
        })
        
        # 3. Vérifier la redirection après login
        assert login_post_response.status_code == 302
        
        # 4. Suivre la redirection et vérifier l'accès au dashboard
        dashboard_response = client.get(login_post_response.url, follow=True)
        assert dashboard_response.status_code == 200
        
        # 5. Vérifier que l'utilisateur est bien connecté
        assert '_auth_user_id' in client.session
        assert int(client.session['_auth_user_id']) == normal_user.id
    
    def test_admin_login_to_finance_dashboard_flow(self, client, admin_user):
        """
        Flux admin: login → accès dashboard finance.
        
        **Validates: Requirements 24.3**
        """
        # 1. Login admin
        client.force_login(admin_user)
        
        # 2. Accéder au dashboard finance (nécessite rôle admin/finance)
        finance_response = client.get(reverse('finance:dashboard'))
        assert finance_response.status_code == 200
        
        # 3. Vérifier que le contenu finance est présent
        assert 'finance' in finance_response.content.decode().lower() or 'transaction' in finance_response.content.decode().lower()
    
    def test_membre_blocked_from_finance_flow(self, client, normal_user):
        """
        Flux membre: login → tentative accès finance → blocage.
        
        **Validates: Requirements 24.3**
        """
        # 1. Login membre
        client.force_login(normal_user)
        
        # 2. Tenter d'accéder au dashboard finance
        finance_response = client.get(reverse('finance:dashboard'))
        
        # 3. Vérifier le blocage (redirection)
        assert finance_response.status_code == 302
        
        # 4. Suivre la redirection et vérifier le message d'erreur
        follow_response = client.get(finance_response.url, follow=True)
        messages = list(get_messages(follow_response.wsgi_request))
        
        # Vérifier qu'un message d'erreur de permission est présent
        assert len(messages) > 0
        message_texts = [str(msg).lower() for msg in messages]
        assert any('permission' in text or 'autorisé' in text or 'accès' in text for text in message_texts)
    
    def test_finance_user_access_flow(self, client, finance_user):
        """
        Flux utilisateur finance: login → accès modules finance.
        
        **Validates: Requirements 24.3**
        """
        # 1. Login utilisateur finance
        client.force_login(finance_user)
        
        # 2. Accéder au dashboard finance
        dashboard_response = client.get(reverse('finance:dashboard'))
        assert dashboard_response.status_code == 200
        
        # 3. Accéder à la création de transaction
        create_response = client.get(reverse('finance:transaction_create'))
        assert create_response.status_code == 200
        
        # 4. Accéder à la liste des transactions
        list_response = client.get(reverse('finance:transaction_list'))
        assert list_response.status_code == 200


class TestPasswordChangeFlow:
    """
    Tests d'intégration pour le flux de changement de mot de passe.
    
    **Validates: Requirements 24.3**
    """
    
    @pytest.fixture
    def client(self):
        """Client de test."""
        return Client()
    
    @pytest.fixture
    def must_change_user(self, db):
        """Utilisateur devant changer son mot de passe."""
        return User.objects.create_user(
            username='password_change_test',
            password='temp123',
            first_name='Password',
            last_name='Change',
            role='membre',
            must_change_password=True
        )
    
    def test_complete_password_change_flow(self, client, must_change_user):
        """
        Flux complet de changement de mot de passe obligatoire.
        
        **Validates: Requirements 24.3**
        """
        # 1. Login avec utilisateur devant changer son mot de passe
        login_response = client.post(reverse('accounts:login'), {
            'username': 'password_change_test',
            'password': 'temp123'
        })
        
        # 2. Vérifier la redirection vers changement de mot de passe
        assert login_response.status_code == 302
        assert 'first-login-password-change' in login_response.url or 'first_login_password_change' in login_response.url
        assert 'token=' in login_response.url
        
        # 3. Extraire le token de l'URL
        token = login_response.url.split('token=')[1].split('&')[0]
        
        # 4. Accéder à la page de changement de mot de passe
        change_url = reverse('accounts:first_login_password_change')
        change_response = client.get(f"{change_url}?token={token}")
        assert change_response.status_code == 200
        
        # 5. Soumettre le nouveau mot de passe
        new_password_response = client.post(f"{change_url}?token={token}", {
            'new_password1': 'NewSecurePassword123!',
            'new_password2': 'NewSecurePassword123!'
        })
        
        # 6. Vérifier la redirection après changement
        assert new_password_response.status_code == 302
        
        # 7. Vérifier que l'utilisateur peut maintenant se connecter avec le nouveau mot de passe
        client.logout()
        final_login = client.post(reverse('accounts:login'), {
            'username': 'password_change_test',
            'password': 'NewSecurePassword123!'
        })
        assert final_login.status_code == 302
        
        # 8. Vérifier que must_change_password est maintenant False
        must_change_user.refresh_from_db()
        assert must_change_user.must_change_password is False
    
    def test_invalid_token_flow(self, client, must_change_user):
        """
        Flux avec token invalide.
        
        **Validates: Requirements 24.3**
        """
        # 1. Tenter d'accéder avec un token invalide
        change_url = reverse('accounts:first_login_password_change')
        response = client.get(f"{change_url}?token=invalid_token")
        
        # 2. Vérifier la redirection ou l'erreur
        assert response.status_code in [302, 403, 404]
    
    def test_expired_token_flow(self, client, must_change_user):
        """
        Flux avec token expiré.
        
        **Validates: Requirements 24.3**
        """
        # 1. Générer un token
        token = AuthenticationService.generate_password_change_token(must_change_user)
        
        # 2. Simuler l'expiration en modifiant directement en base
        from apps.accounts.models import PasswordChangeToken
        token_obj = PasswordChangeToken.objects.filter(token=token).first()
        if token_obj:
            token_obj.expires_at = timezone.now() - timedelta(hours=1)
            token_obj.save()
        
        # 3. Tenter d'utiliser le token expiré
        change_url = reverse('accounts:first_login_password_change')
        response = client.get(f"{change_url}?token={token}")
        
        # 4. Vérifier le rejet
        assert response.status_code in [302, 403, 404]


class TestAuditLoggingIntegration:
    """
    Tests d'intégration pour l'audit logging.
    
    **Validates: Requirements 24.3**
    """
    
    @pytest.fixture
    def client(self):
        """Client de test."""
        return Client()
    
    @pytest.fixture
    def admin_user(self, db):
        """Utilisateur admin."""
        return User.objects.create_user(
            username='audit_admin',
            password='audit123',
            first_name='Audit',
            last_name='Admin',
            role='admin'
        )
    
    def test_login_creates_audit_log(self, client, admin_user):
        """
        Le login crée une entrée d'audit log.
        
        **Validates: Requirements 24.3**
        """
        # Compter les logs avant
        initial_count = AuditLog.objects.count()
        
        # Login
        client.post(reverse('accounts:login'), {
            'username': 'audit_admin',
            'password': 'audit123'
        })
        
        # Vérifier qu'un log a été créé
        final_count = AuditLog.objects.count()
        assert final_count > initial_count
        
        # Vérifier le contenu du log
        login_log = AuditLog.objects.filter(
            user=admin_user,
            action=AuditLog.Action.LOGIN
        ).first()
        
        assert login_log is not None
        assert login_log.user == admin_user
    
    def test_failed_login_creates_audit_log(self, client, admin_user):
        """
        Un login échoué crée une entrée d'audit log.
        
        **Validates: Requirements 24.3**
        """
        # Compter les logs avant
        initial_count = AuditLog.objects.count()
        
        # Tentative de login échouée
        client.post(reverse('accounts:login'), {
            'username': 'audit_admin',
            'password': 'wrong_password'
        })
        
        # Vérifier qu'un log a été créé
        final_count = AuditLog.objects.count()
        assert final_count > initial_count
        
        # Vérifier le contenu du log
        failed_log = AuditLog.objects.filter(
            action=AuditLog.Action.LOGIN_FAILED
        ).order_by('-timestamp').first()
        
        assert failed_log is not None
    
    def test_export_creates_audit_log(self, client, admin_user):
        """
        Un export crée une entrée d'audit log.
        
        **Validates: Requirements 24.3**
        """
        # Login
        client.force_login(admin_user)
        
        # Compter les logs avant
        initial_count = AuditLog.objects.count()
        
        # Effectuer un export
        client.get(reverse('core:members_export_excel'))
        
        # Vérifier qu'un log a été créé
        final_count = AuditLog.objects.count()
        assert final_count > initial_count
        
        # Vérifier le contenu du log
        export_log = AuditLog.objects.filter(
            user=admin_user,
            action=AuditLog.Action.EXPORT
        ).order_by('-timestamp').first()
        
        assert export_log is not None
        assert export_log.user == admin_user


class TestCrossModuleNavigation:
    """
    Tests d'intégration pour la navigation entre modules.
    
    **Validates: Requirements 24.3**
    """
    
    @pytest.fixture
    def client(self):
        """Client de test."""
        return Client()
    
    @pytest.fixture
    def admin_user(self, db):
        """Utilisateur admin."""
        return User.objects.create_user(
            username='nav_admin',
            password='nav123',
            role='admin'
        )
    
    @pytest.fixture
    def finance_user(self, db):
        """Utilisateur finance."""
        return User.objects.create_user(
            username='nav_finance',
            password='nav123',
            role='finance'
        )
    
    @pytest.fixture
    def membre_user(self, db):
        """Utilisateur membre."""
        return User.objects.create_user(
            username='nav_membre',
            password='nav123',
            role='membre'
        )
    
    def test_admin_can_navigate_all_modules(self, client, admin_user):
        """
        Un admin peut naviguer dans tous les modules.
        
        **Validates: Requirements 24.3**
        """
        client.force_login(admin_user)
        
        # Tester l'accès à différents modules
        modules_to_test = [
            'dashboard:home',
            'finance:dashboard',
            'members:member_list',
            'accounts:user_list',
        ]
        
        for module_url in modules_to_test:
            response = client.get(reverse(module_url))
            assert response.status_code == 200, f"Admin should access {module_url}"
    
    def test_finance_user_restricted_navigation(self, client, finance_user):
        """
        Un utilisateur finance a un accès restreint.
        
        **Validates: Requirements 24.3**
        """
        client.force_login(finance_user)
        
        # Modules autorisés
        allowed_modules = [
            'finance:dashboard',
            'finance:transaction_list',
        ]
        
        for module_url in allowed_modules:
            response = client.get(reverse(module_url))
            assert response.status_code == 200, f"Finance user should access {module_url}"
        
        # Modules interdits
        forbidden_modules = [
            'accounts:user_list',  # Gestion des utilisateurs réservée admin/secretariat
        ]
        
        for module_url in forbidden_modules:
            response = client.get(reverse(module_url))
            assert response.status_code == 302, f"Finance user should not access {module_url}"
    
    def test_membre_very_restricted_navigation(self, client, membre_user):
        """
        Un membre a un accès très restreint.
        
        **Validates: Requirements 24.3**
        """
        client.force_login(membre_user)
        
        # Modules autorisés (lecture seule)
        allowed_modules = [
            'members:member_list',  # Liste des membres en lecture seule
        ]
        
        for module_url in allowed_modules:
            response = client.get(reverse(module_url))
            assert response.status_code == 200, f"Membre should access {module_url}"
        
        # Modules interdits
        forbidden_modules = [
            'finance:dashboard',
            'finance:transaction_create',
            'accounts:user_list',
        ]
        
        for module_url in forbidden_modules:
            response = client.get(reverse(module_url))
            assert response.status_code == 302, f"Membre should not access {module_url}"


class TestDataCreationFlow:
    """
    Tests d'intégration pour les flux de création de données.
    
    **Validates: Requirements 24.3**
    """
    
    @pytest.fixture
    def client(self):
        """Client de test."""
        return Client()
    
    @pytest.fixture
    def finance_user(self, db):
        """Utilisateur finance."""
        return User.objects.create_user(
            username='data_finance',
            password='data123',
            role='finance'
        )
    
    def test_transaction_creation_flow(self, client, finance_user):
        """
        Flux complet de création de transaction.
        
        **Validates: Requirements 24.3**
        """
        # 1. Login
        client.force_login(finance_user)
        
        # 2. Accéder au formulaire de création
        create_response = client.get(reverse('finance:transaction_create'))
        assert create_response.status_code == 200
        
        # 3. Soumettre une nouvelle transaction
        transaction_data = {
            'transaction_type': FinancialTransaction.TransactionType.DON,
            'amount': '150.75',
            'transaction_date': '2024-01-15',
            'payment_method': FinancialTransaction.PaymentMethod.VIREMENT,
            'description': 'Don de test intégration'
        }
        
        post_response = client.post(reverse('finance:transaction_create'), transaction_data)
        
        # 4. Vérifier la redirection après création
        assert post_response.status_code == 302
        
        # 5. Vérifier que la transaction a été créée
        transaction = FinancialTransaction.objects.filter(
            amount=Decimal('150.75'),
            recorded_by=finance_user
        ).first()
        
        assert transaction is not None
        assert transaction.transaction_type == FinancialTransaction.TransactionType.DON
        assert transaction.description == 'Don de test intégration'
        
        # 6. Vérifier que l'audit log a été créé
        audit_log = AuditLog.objects.filter(
            user=finance_user,
            action=AuditLog.Action.CREATE,
            model_name='FinancialTransaction'
        ).first()
        
        assert audit_log is not None


class TestSessionManagement:
    """
    Tests d'intégration pour la gestion des sessions.
    
    **Validates: Requirements 24.3**
    """
    
    @pytest.fixture
    def client(self):
        """Client de test."""
        return Client()
    
    @pytest.fixture
    def test_user(self, db):
        """Utilisateur de test."""
        return User.objects.create_user(
            username='session_test',
            password='session123',
            role='membre'
        )
    
    def test_session_persistence_across_requests(self, client, test_user):
        """
        La session persiste entre les requêtes.
        
        **Validates: Requirements 24.3**
        """
        # 1. Login
        login_response = client.post(reverse('accounts:login'), {
            'username': 'session_test',
            'password': 'session123'
        })
        assert login_response.status_code == 302
        
        # 2. Vérifier que la session est active
        assert '_auth_user_id' in client.session
        
        # 3. Faire plusieurs requêtes et vérifier la persistance
        for _ in range(3):
            response = client.get(reverse('members:member_list'))
            assert response.status_code == 200
            assert '_auth_user_id' in client.session
    
    def test_logout_clears_session(self, client, test_user):
        """
        Le logout nettoie la session.
        
        **Validates: Requirements 24.3**
        """
        # 1. Login
        client.force_login(test_user)
        assert '_auth_user_id' in client.session
        
        # 2. Logout
        logout_response = client.post(reverse('accounts:logout'))
        assert logout_response.status_code == 302
        
        # 3. Vérifier que la session est nettoyée
        assert '_auth_user_id' not in client.session
        
        # 4. Vérifier qu'on ne peut plus accéder aux pages protégées
        protected_response = client.get(reverse('finance:dashboard'))
        assert protected_response.status_code == 302  # Redirection vers login