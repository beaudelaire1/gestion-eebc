"""
Tests de protection des exports de données.

Property 2: Export Permission Verification
Pour toute opération d'export et tout utilisateur, l'export réussit si et seulement si
l'utilisateur a le rôle approprié pour ce type de données:
- admin/secretariat pour les membres
- admin/responsable_club pour les enfants
- admin/finance pour les transactions/budgets

Validates: Requirements 4.1, 4.2, 4.3, 4.4
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
# EXPORT PERMISSION CONFIGURATION
# =============================================================================

# Configuration des exports et leurs rôles autorisés
EXPORT_CONFIGS = {
    # Membres: admin, secretariat (Requirement 4.1)
    'members': {
        'url_name': 'exports:members_excel',
        'authorized_roles': ['admin', 'secretariat'],
        'unauthorized_roles': ['finance', 'responsable_club', 'moniteur', 'responsable_groupe', 'encadrant', 'membre'],
        'requirement': '4.1',
    },
    'members_print': {
        'url_name': 'exports:members_print',
        'authorized_roles': ['admin', 'secretariat'],
        'unauthorized_roles': ['finance', 'responsable_club', 'moniteur', 'responsable_groupe', 'encadrant', 'membre'],
        'requirement': '4.1',
    },
    
    # Enfants du club biblique: admin, responsable_club (Requirement 4.2)
    'children': {
        'url_name': 'exports:children_excel',
        'authorized_roles': ['admin', 'responsable_club'],
        'unauthorized_roles': ['finance', 'secretariat', 'moniteur', 'responsable_groupe', 'encadrant', 'membre'],
        'requirement': '4.2',
    },
    'children_print': {
        'url_name': 'exports:children_print',
        'authorized_roles': ['admin', 'responsable_club'],
        'unauthorized_roles': ['finance', 'secretariat', 'moniteur', 'responsable_groupe', 'encadrant', 'membre'],
        'requirement': '4.2',
    },
    'attendance': {
        'url_name': 'exports:attendance_excel',
        'authorized_roles': ['admin', 'responsable_club'],
        'unauthorized_roles': ['finance', 'secretariat', 'moniteur', 'responsable_groupe', 'encadrant', 'membre'],
        'requirement': '4.2',
    },
    
    # Transactions: admin, finance (Requirement 4.3)
    'transactions': {
        'url_name': 'exports:transactions_excel',
        'authorized_roles': ['admin', 'finance'],
        'unauthorized_roles': ['secretariat', 'responsable_club', 'moniteur', 'responsable_groupe', 'encadrant', 'membre'],
        'requirement': '4.3',
    },
    
    # Budgets: admin, finance (Requirement 4.4)
    'budgets': {
        'url_name': 'exports:budgets_excel',
        'authorized_roles': ['admin', 'finance'],
        'unauthorized_roles': ['secretariat', 'responsable_club', 'moniteur', 'responsable_groupe', 'encadrant', 'membre'],
        'requirement': '4.4',
    },
    'budgets_print': {
        'url_name': 'exports:budgets_print',
        'authorized_roles': ['admin', 'finance'],
        'unauthorized_roles': ['secretariat', 'responsable_club', 'moniteur', 'responsable_groupe', 'encadrant', 'membre'],
        'requirement': '4.4',
    },
}


# =============================================================================
# TESTS DE PROTECTION DES EXPORTS MEMBRES (Requirement 4.1)
# =============================================================================

class TestMembersExportProtection:
    """Tests de protection des exports de membres.
    
    **Validates: Requirements 4.1**
    """
    
    def test_members_export_requires_login(self, client, db):
        """
        L'export des membres requiert une authentification.
        
        **Validates: Requirements 4.1**
        """
        response = client.get(reverse('exports:members_excel'))
        assert response.status_code == 302
        assert '/login/' in response.url or '/accounts/login/' in response.url
    
    def test_members_export_accessible_by_admin(self, client, db, admin_user):
        """
        L'export des membres est accessible par un admin.
        
        **Validates: Requirements 4.1**
        """
        client.force_login(admin_user)
        response = client.get(reverse('exports:members_excel'))
        # 200 pour succès ou 302 si redirection vers une autre page (pas login)
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert '/login/' not in response.url
    
    def test_members_export_accessible_by_secretariat(self, client, db, secretariat_user):
        """
        L'export des membres est accessible par le secrétariat.
        
        **Validates: Requirements 4.1**
        """
        client.force_login(secretariat_user)
        response = client.get(reverse('exports:members_excel'))
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert '/login/' not in response.url
    
    def test_members_export_denied_to_finance(self, client, db, finance_user):
        """
        L'export des membres est refusé à un utilisateur finance.
        
        **Validates: Requirements 4.1**
        """
        client.force_login(finance_user)
        response = client.get(reverse('exports:members_excel'))
        assert response.status_code == 302
    
    def test_members_export_denied_to_membre(self, client, db, membre_user):
        """
        L'export des membres est refusé à un membre.
        
        **Validates: Requirements 4.1**
        """
        client.force_login(membre_user)
        response = client.get(reverse('exports:members_excel'))
        assert response.status_code == 302
    
    def test_members_print_requires_login(self, client, db):
        """
        L'impression PDF des membres requiert une authentification.
        
        **Validates: Requirements 4.1**
        """
        response = client.get(reverse('exports:members_print'))
        assert response.status_code == 302
    
    def test_members_print_accessible_by_secretariat(self, client, db, secretariat_user):
        """
        L'impression PDF des membres est accessible par le secrétariat.
        
        **Validates: Requirements 4.1**
        """
        client.force_login(secretariat_user)
        response = client.get(reverse('exports:members_print'))
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert '/login/' not in response.url


# =============================================================================
# TESTS DE PROTECTION DES EXPORTS ENFANTS (Requirement 4.2)
# =============================================================================

class TestChildrenExportProtection:
    """Tests de protection des exports d'enfants du club biblique.
    
    **Validates: Requirements 4.2**
    """
    
    def test_children_export_requires_login(self, client, db):
        """
        L'export des enfants requiert une authentification.
        
        **Validates: Requirements 4.2**
        """
        response = client.get(reverse('exports:children_excel'))
        assert response.status_code == 302
        assert '/login/' in response.url or '/accounts/login/' in response.url
    
    def test_children_export_accessible_by_admin(self, client, db, admin_user):
        """
        L'export des enfants est accessible par un admin.
        
        **Validates: Requirements 4.2**
        """
        client.force_login(admin_user)
        response = client.get(reverse('exports:children_excel'))
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert '/login/' not in response.url
    
    def test_children_export_accessible_by_responsable_club(self, client, db, responsable_club_user):
        """
        L'export des enfants est accessible par le responsable du club.
        
        **Validates: Requirements 4.2**
        """
        client.force_login(responsable_club_user)
        response = client.get(reverse('exports:children_excel'))
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert '/login/' not in response.url
    
    def test_children_export_denied_to_secretariat(self, client, db, secretariat_user):
        """
        L'export des enfants est refusé au secrétariat.
        
        **Validates: Requirements 4.2**
        """
        client.force_login(secretariat_user)
        response = client.get(reverse('exports:children_excel'))
        assert response.status_code == 302
    
    def test_children_export_denied_to_finance(self, client, db, finance_user):
        """
        L'export des enfants est refusé à un utilisateur finance.
        
        **Validates: Requirements 4.2**
        """
        client.force_login(finance_user)
        response = client.get(reverse('exports:children_excel'))
        assert response.status_code == 302
    
    def test_children_export_denied_to_membre(self, client, db, membre_user):
        """
        L'export des enfants est refusé à un membre.
        
        **Validates: Requirements 4.2**
        """
        client.force_login(membre_user)
        response = client.get(reverse('exports:children_excel'))
        assert response.status_code == 302
    
    def test_attendance_export_accessible_by_responsable_club(self, client, db, responsable_club_user):
        """
        L'export des présences est accessible par le responsable du club.
        
        **Validates: Requirements 4.2**
        """
        client.force_login(responsable_club_user)
        response = client.get(reverse('exports:attendance_excel'))
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert '/login/' not in response.url


# =============================================================================
# TESTS DE PROTECTION DES EXPORTS TRANSACTIONS (Requirement 4.3)
# =============================================================================

class TestTransactionsExportProtection:
    """Tests de protection des exports de transactions.
    
    **Validates: Requirements 4.3**
    """
    
    def test_transactions_export_requires_login(self, client, db):
        """
        L'export des transactions requiert une authentification.
        
        **Validates: Requirements 4.3**
        """
        response = client.get(reverse('exports:transactions_excel'))
        assert response.status_code == 302
        assert '/login/' in response.url or '/accounts/login/' in response.url
    
    def test_transactions_export_accessible_by_admin(self, client, db, admin_user):
        """
        L'export des transactions est accessible par un admin.
        
        **Validates: Requirements 4.3**
        """
        client.force_login(admin_user)
        response = client.get(reverse('exports:transactions_excel'))
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert '/login/' not in response.url
    
    def test_transactions_export_accessible_by_finance(self, client, db, finance_user):
        """
        L'export des transactions est accessible par un utilisateur finance.
        
        **Validates: Requirements 4.3**
        """
        client.force_login(finance_user)
        response = client.get(reverse('exports:transactions_excel'))
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert '/login/' not in response.url
    
    def test_transactions_export_denied_to_secretariat(self, client, db, secretariat_user):
        """
        L'export des transactions est refusé au secrétariat.
        
        **Validates: Requirements 4.3**
        """
        client.force_login(secretariat_user)
        response = client.get(reverse('exports:transactions_excel'))
        assert response.status_code == 302
    
    def test_transactions_export_denied_to_membre(self, client, db, membre_user):
        """
        L'export des transactions est refusé à un membre.
        
        **Validates: Requirements 4.3**
        """
        client.force_login(membre_user)
        response = client.get(reverse('exports:transactions_excel'))
        assert response.status_code == 302


# =============================================================================
# TESTS DE PROTECTION DES EXPORTS BUDGETS (Requirement 4.4)
# =============================================================================

class TestBudgetsExportProtection:
    """Tests de protection des exports de budgets.
    
    **Validates: Requirements 4.4**
    """
    
    def test_budgets_export_requires_login(self, client, db):
        """
        L'export des budgets requiert une authentification.
        
        **Validates: Requirements 4.4**
        """
        response = client.get(reverse('exports:budgets_excel'))
        assert response.status_code == 302
        assert '/login/' in response.url or '/accounts/login/' in response.url
    
    def test_budgets_export_accessible_by_admin(self, client, db, admin_user):
        """
        L'export des budgets est accessible par un admin.
        
        **Validates: Requirements 4.4**
        """
        client.force_login(admin_user)
        response = client.get(reverse('exports:budgets_excel'))
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert '/login/' not in response.url
    
    def test_budgets_export_accessible_by_finance(self, client, db, finance_user):
        """
        L'export des budgets est accessible par un utilisateur finance.
        
        **Validates: Requirements 4.4**
        """
        client.force_login(finance_user)
        response = client.get(reverse('exports:budgets_excel'))
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert '/login/' not in response.url
    
    def test_budgets_export_denied_to_secretariat(self, client, db, secretariat_user):
        """
        L'export des budgets est refusé au secrétariat.
        
        **Validates: Requirements 4.4**
        """
        client.force_login(secretariat_user)
        response = client.get(reverse('exports:budgets_excel'))
        assert response.status_code == 302
    
    def test_budgets_export_denied_to_membre(self, client, db, membre_user):
        """
        L'export des budgets est refusé à un membre.
        
        **Validates: Requirements 4.4**
        """
        client.force_login(membre_user)
        response = client.get(reverse('exports:budgets_excel'))
        assert response.status_code == 302
    
    def test_budgets_print_accessible_by_finance(self, client, db, finance_user):
        """
        L'impression PDF des budgets est accessible par un utilisateur finance.
        
        **Validates: Requirements 4.4**
        """
        client.force_login(finance_user)
        response = client.get(reverse('exports:budgets_print'))
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert '/login/' not in response.url


# =============================================================================
# PROPERTY-BASED TESTS
# =============================================================================

class TestExportPermissionVerificationProperty:
    """
    Property 2: Export Permission Verification
    
    Pour toute opération d'export et tout utilisateur, l'export réussit si et seulement si
    l'utilisateur a le rôle approprié pour ce type de données.
    
    **Feature: security-audit-fixes, Property 2: Export Permission Verification**
    **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
    """
    
    # URLs d'export à tester avec leurs rôles autorisés
    EXPORT_PERMISSION_MATRIX = [
        # (url_name, authorized_roles, requirement)
        # Membres (Requirement 4.1)
        ('exports:members_excel', ('admin', 'secretariat'), '4.1'),
        ('exports:members_print', ('admin', 'secretariat'), '4.1'),
        
        # Enfants (Requirement 4.2)
        ('exports:children_excel', ('admin', 'responsable_club'), '4.2'),
        ('exports:children_print', ('admin', 'responsable_club'), '4.2'),
        ('exports:attendance_excel', ('admin', 'responsable_club'), '4.2'),
        
        # Transactions (Requirement 4.3)
        ('exports:transactions_excel', ('admin', 'finance'), '4.3'),
        
        # Budgets (Requirement 4.4)
        ('exports:budgets_excel', ('admin', 'finance'), '4.4'),
        ('exports:budgets_print', ('admin', 'finance'), '4.4'),
    ]
    
    ALL_ROLES = ['admin', 'secretariat', 'finance', 'responsable_club', 
                 'moniteur', 'responsable_groupe', 'encadrant', 'membre']
    
    @pytest.mark.parametrize("url_name,authorized_roles,requirement", EXPORT_PERMISSION_MATRIX)
    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_export_permission_enforcement(self, client, db, url_name, authorized_roles, requirement, role):
        """
        Property 2: Export Permission Verification
        
        Pour tout rôle et tout type d'export, l'accès est accordé si et seulement si
        le rôle est dans la liste des rôles autorisés pour cet export.
        
        **Feature: security-audit-fixes, Property 2: Export Permission Verification**
        **Validates: Requirements {requirement}**
        """
        # Créer un utilisateur avec ce rôle
        user = User.objects.create_user(
            username=f'test_{role}_{url_name.replace(":", "_")}_{requirement}',
            password='testpass123',
            role=role
        )
        client.force_login(user)
        
        response = client.get(reverse(url_name))
        
        # Vérifier si l'accès est accordé ou refusé selon le rôle
        is_authorized = role in authorized_roles
        
        if is_authorized:
            # L'utilisateur autorisé devrait avoir accès (200 ou redirection non-login)
            assert response.status_code in [200, 302], (
                f"L'utilisateur avec rôle '{role}' devrait avoir accès à {url_name} "
                f"(Requirement {requirement})"
            )
            if response.status_code == 302:
                assert '/login/' not in response.url, (
                    f"L'utilisateur avec rôle '{role}' ne devrait pas être redirigé vers login "
                    f"pour {url_name} (Requirement {requirement})"
                )
        else:
            # L'utilisateur non autorisé devrait être refusé (redirection)
            assert response.status_code == 302, (
                f"L'utilisateur avec rôle '{role}' ne devrait pas avoir accès à {url_name} "
                f"(Requirement {requirement})"
            )
    
    @pytest.mark.parametrize("url_name,authorized_roles,requirement", EXPORT_PERMISSION_MATRIX)
    def test_superuser_can_access_all_exports(self, client, db, superuser, url_name, authorized_roles, requirement):
        """
        Property: Un superuser peut accéder à tous les exports.
        
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
        """
        client.force_login(superuser)
        response = client.get(reverse(url_name))
        
        assert response.status_code in [200, 302], (
            f"Le superuser devrait avoir accès à {url_name}"
        )
        if response.status_code == 302:
            assert '/login/' not in response.url, (
                f"Le superuser ne devrait pas être redirigé vers login pour {url_name}"
            )
    
    @pytest.mark.parametrize("url_name,authorized_roles,requirement", EXPORT_PERMISSION_MATRIX)
    def test_anonymous_cannot_access_exports(self, client, db, url_name, authorized_roles, requirement):
        """
        Property: Un utilisateur anonyme ne peut accéder à aucun export.
        
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
        """
        response = client.get(reverse(url_name))
        
        assert response.status_code == 302, (
            f"Un utilisateur anonyme ne devrait pas avoir accès à {url_name}"
        )
        assert '/login/' in response.url or '/accounts/login/' in response.url, (
            f"Un utilisateur anonyme devrait être redirigé vers login pour {url_name}"
        )
