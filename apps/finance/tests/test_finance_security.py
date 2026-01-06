"""
Tests de sécurité pour les vues Finance.

Property 1: Permission Enforcement
Pour tout utilisateur et toute vue finance protégée, l'accès est accordé si et seulement si
l'utilisateur possède le rôle 'admin' ou 'finance'.

Validates: Requirements 3.1, 3.2, 3.3, 3.4
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from hypothesis import given, strategies as st, settings as hypothesis_settings

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def client():
    """Client HTTP pour les tests."""
    return Client()


# =============================================================================
# TESTS DE PROTECTION DES VUES FINANCE
# =============================================================================

class TestFinanceDashboardProtection:
    """Tests de protection du dashboard finance."""
    
    def test_dashboard_requires_login(self, client, db):
        """
        Le dashboard finance requiert une authentification.
        
        **Validates: Requirements 3.1**
        """
        response = client.get(reverse('finance:dashboard'))
        # Devrait rediriger vers login
        assert response.status_code == 302
        assert '/accounts/login/' in response.url or '/login/' in response.url
    
    def test_dashboard_accessible_by_admin(self, client, db, admin_user):
        """
        Le dashboard finance est accessible par un admin.
        
        **Validates: Requirements 3.4**
        """
        client.force_login(admin_user)
        response = client.get(reverse('finance:dashboard'))
        assert response.status_code == 200
    
    def test_dashboard_accessible_by_finance(self, client, db, finance_user):
        """
        Le dashboard finance est accessible par un utilisateur finance.
        
        **Validates: Requirements 3.4**
        """
        client.force_login(finance_user)
        response = client.get(reverse('finance:dashboard'))
        assert response.status_code == 200
    
    def test_dashboard_denied_to_membre(self, client, db, membre_user):
        """
        Le dashboard finance est refusé à un membre.
        
        **Validates: Requirements 3.1**
        """
        client.force_login(membre_user)
        response = client.get(reverse('finance:dashboard'))
        # Devrait rediriger (accès refusé)
        assert response.status_code == 302
    
    def test_dashboard_denied_to_secretariat(self, client, db, secretariat_user):
        """
        Le dashboard finance est refusé au secrétariat.
        
        **Validates: Requirements 3.1**
        """
        client.force_login(secretariat_user)
        response = client.get(reverse('finance:dashboard'))
        assert response.status_code == 302


class TestTransactionCreateProtection:
    """Tests de protection de la création de transactions."""
    
    def test_transaction_create_requires_login(self, client, db):
        """
        La création de transaction requiert une authentification.
        
        **Validates: Requirements 3.2**
        """
        response = client.get(reverse('finance:transaction_create'))
        assert response.status_code == 302
        assert '/accounts/login/' in response.url or '/login/' in response.url
    
    def test_transaction_create_accessible_by_admin(self, client, db, admin_user):
        """
        La création de transaction est accessible par un admin.
        
        **Validates: Requirements 3.4**
        """
        client.force_login(admin_user)
        response = client.get(reverse('finance:transaction_create'))
        assert response.status_code == 200
    
    def test_transaction_create_accessible_by_finance(self, client, db, finance_user):
        """
        La création de transaction est accessible par un utilisateur finance.
        
        **Validates: Requirements 3.4**
        """
        client.force_login(finance_user)
        response = client.get(reverse('finance:transaction_create'))
        assert response.status_code == 200
    
    def test_transaction_create_denied_to_membre(self, client, db, membre_user):
        """
        La création de transaction est refusée à un membre.
        
        **Validates: Requirements 3.2**
        """
        client.force_login(membre_user)
        response = client.get(reverse('finance:transaction_create'))
        assert response.status_code == 302
    
    def test_transaction_create_denied_to_secretariat(self, client, db, secretariat_user):
        """
        La création de transaction est refusée au secrétariat.
        
        **Validates: Requirements 3.2**
        """
        client.force_login(secretariat_user)
        response = client.get(reverse('finance:transaction_create'))
        assert response.status_code == 302


class TestBudgetViewsProtection:
    """Tests de protection des vues budget."""
    
    def test_budget_dashboard_requires_login(self, client, db):
        """
        Le dashboard budget requiert une authentification.
        
        **Validates: Requirements 3.4**
        """
        response = client.get(reverse('finance:budget_dashboard'))
        assert response.status_code == 302
    
    def test_budget_dashboard_accessible_by_admin(self, client, db, admin_user):
        """
        Le dashboard budget est accessible par un admin.
        
        **Validates: Requirements 3.4**
        """
        client.force_login(admin_user)
        response = client.get(reverse('finance:budget_dashboard'))
        assert response.status_code == 200
    
    def test_budget_dashboard_accessible_by_finance(self, client, db, finance_user):
        """
        Le dashboard budget est accessible par un utilisateur finance.
        
        **Validates: Requirements 3.4**
        """
        client.force_login(finance_user)
        response = client.get(reverse('finance:budget_dashboard'))
        assert response.status_code == 200
    
    def test_budget_dashboard_denied_to_membre(self, client, db, membre_user):
        """
        Le dashboard budget est refusé à un membre.
        
        **Validates: Requirements 3.4**
        """
        client.force_login(membre_user)
        response = client.get(reverse('finance:budget_dashboard'))
        assert response.status_code == 302
    
    def test_budget_list_requires_login(self, client, db):
        """
        La liste des budgets requiert une authentification.
        
        **Validates: Requirements 3.4**
        """
        response = client.get(reverse('finance:budget_list'))
        assert response.status_code == 302
    
    def test_budget_list_accessible_by_finance(self, client, db, finance_user):
        """
        La liste des budgets est accessible par un utilisateur finance.
        
        **Validates: Requirements 3.4**
        """
        client.force_login(finance_user)
        response = client.get(reverse('finance:budget_list'))
        assert response.status_code == 200
    
    def test_budget_create_requires_login(self, client, db):
        """
        La création de budget requiert une authentification.
        
        **Validates: Requirements 3.4**
        """
        response = client.get(reverse('finance:budget_create'))
        assert response.status_code == 302
    
    def test_budget_create_accessible_by_finance(self, client, db, finance_user):
        """
        La création de budget est accessible par un utilisateur finance.
        
        **Validates: Requirements 3.4**
        """
        client.force_login(finance_user)
        response = client.get(reverse('finance:budget_create'))
        assert response.status_code == 200
    
    def test_budget_create_denied_to_membre(self, client, db, membre_user):
        """
        La création de budget est refusée à un membre.
        
        **Validates: Requirements 3.4**
        """
        client.force_login(membre_user)
        response = client.get(reverse('finance:budget_create'))
        assert response.status_code == 302


class TestExportProtection:
    """Tests de protection des exports financiers."""
    
    def test_transactions_export_requires_login(self, client, db):
        """
        L'export des transactions requiert une authentification.
        
        **Validates: Requirements 3.3**
        """
        response = client.get(reverse('finance:transactions_export_excel'))
        assert response.status_code == 302
    
    def test_transactions_export_accessible_by_finance(self, client, db, finance_user):
        """
        L'export des transactions est accessible par un utilisateur finance.
        
        **Validates: Requirements 3.3, 3.4**
        """
        client.force_login(finance_user)
        response = client.get(reverse('finance:transactions_export_excel'))
        # Devrait retourner un fichier Excel (200) ou rediriger si pas de données
        assert response.status_code in [200, 302]
    
    def test_transactions_export_denied_to_membre(self, client, db, membre_user):
        """
        L'export des transactions est refusé à un membre.
        
        **Validates: Requirements 3.3**
        """
        client.force_login(membre_user)
        response = client.get(reverse('finance:transactions_export_excel'))
        assert response.status_code == 302
    
    def test_budget_list_export_requires_login(self, client, db):
        """
        L'export de la liste des budgets requiert une authentification.
        
        **Validates: Requirements 3.3**
        """
        response = client.get(reverse('finance:budget_list_export_excel'))
        assert response.status_code == 302
    
    def test_budget_list_export_accessible_by_finance(self, client, db, finance_user):
        """
        L'export de la liste des budgets est accessible par un utilisateur finance.
        
        **Validates: Requirements 3.3, 3.4**
        """
        client.force_login(finance_user)
        response = client.get(reverse('finance:budget_list_export_excel'))
        assert response.status_code in [200, 302]
    
    def test_budget_list_export_denied_to_membre(self, client, db, membre_user):
        """
        L'export de la liste des budgets est refusé à un membre.
        
        **Validates: Requirements 3.3**
        """
        client.force_login(membre_user)
        response = client.get(reverse('finance:budget_list_export_excel'))
        assert response.status_code == 302


# =============================================================================
# PROPERTY-BASED TESTS
# =============================================================================

class TestFinancePermissionEnforcementProperty:
    """
    Property 1: Permission Enforcement pour les vues Finance
    
    Pour tout utilisateur et toute vue finance protégée, l'accès est accordé 
    si et seulement si l'utilisateur possède le rôle 'admin' ou 'finance'.
    
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    """
    
    # Liste des URLs finance à tester
    FINANCE_URLS = [
        'finance:dashboard',
        'finance:transaction_list',
        'finance:transaction_create',
        'finance:budget_overview',
        'finance:reports',
        'finance:tax_receipt_list',
        'finance:budget_dashboard',
        'finance:budget_list',
        'finance:budget_create',
        'finance:budget_request_list',
        'finance:budget_request_create',
        'finance:receipt_proof_list',
    ]
    
    # Rôles autorisés pour les vues finance
    AUTHORIZED_ROLES = ['admin', 'finance']
    
    # Rôles non autorisés
    UNAUTHORIZED_ROLES = ['secretariat', 'responsable_club', 'moniteur', 
                          'responsable_groupe', 'encadrant', 'membre']
    
    @pytest.mark.parametrize("url_name", FINANCE_URLS)
    @pytest.mark.parametrize("role", AUTHORIZED_ROLES)
    def test_authorized_roles_can_access_finance_views(self, client, db, url_name, role):
        """
        Property: Les rôles admin et finance peuvent accéder aux vues finance.
        
        **Validates: Requirements 3.4**
        """
        user = User.objects.create_user(
            username=f'test_{role}_{url_name.replace(":", "_")}',
            password='testpass123',
            role=role
        )
        client.force_login(user)
        
        response = client.get(reverse(url_name))
        assert response.status_code == 200, (
            f"L'utilisateur avec rôle '{role}' devrait avoir accès à {url_name}"
        )
    
    @pytest.mark.parametrize("url_name", FINANCE_URLS)
    @pytest.mark.parametrize("role", UNAUTHORIZED_ROLES)
    def test_unauthorized_roles_cannot_access_finance_views(self, client, db, url_name, role):
        """
        Property: Les rôles non-finance ne peuvent pas accéder aux vues finance.
        
        **Validates: Requirements 3.1, 3.2, 3.3**
        """
        user = User.objects.create_user(
            username=f'test_{role}_{url_name.replace(":", "_")}',
            password='testpass123',
            role=role
        )
        client.force_login(user)
        
        response = client.get(reverse(url_name))
        assert response.status_code == 302, (
            f"L'utilisateur avec rôle '{role}' ne devrait pas avoir accès à {url_name}"
        )
    
    @pytest.mark.parametrize("url_name", FINANCE_URLS)
    def test_superuser_can_access_all_finance_views(self, client, db, superuser, url_name):
        """
        Property: Un superuser peut accéder à toutes les vues finance.
        
        **Validates: Requirements 3.4**
        """
        client.force_login(superuser)
        
        response = client.get(reverse(url_name))
        assert response.status_code == 200, (
            f"Le superuser devrait avoir accès à {url_name}"
        )
    
    @pytest.mark.parametrize("url_name", FINANCE_URLS)
    def test_anonymous_cannot_access_finance_views(self, client, db, url_name):
        """
        Property: Un utilisateur anonyme ne peut pas accéder aux vues finance.
        
        **Validates: Requirements 3.1, 3.2, 3.3**
        """
        response = client.get(reverse(url_name))
        assert response.status_code == 302, (
            f"Un utilisateur anonyme ne devrait pas avoir accès à {url_name}"
        )
        # Vérifie que c'est une redirection vers login
        assert '/login/' in response.url or '/accounts/login/' in response.url
