"""
Tests pour le système de permissions RBAC.

Property 1: Permission Enforcement
Pour tout utilisateur et toute vue protégée, l'accès est accordé si et seulement si
l'utilisateur possède au moins l'un des rôles requis pour cette vue.

Validates: Requirements 2.1, 2.2, 2.3, 2.4
"""

import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.views import View

from apps.core.permissions import (
    has_role,
    get_user_permissions,
    role_required,
    RoleRequiredMixin,
    ROLE_PERMISSIONS,
)

User = get_user_model()


# =============================================================================
# TESTS POUR has_role()
# =============================================================================

class TestHasRole:
    """Tests pour la fonction utilitaire has_role()."""
    
    def test_has_role_with_matching_role(self, db, finance_user):
        """Un utilisateur avec le rôle finance a accès aux vues finance."""
        assert has_role(finance_user, 'finance') is True
    
    def test_has_role_with_non_matching_role(self, db, membre_user):
        """Un utilisateur membre n'a pas accès aux vues finance."""
        assert has_role(membre_user, 'finance') is False
    
    def test_has_role_with_multiple_roles(self, db, finance_user):
        """has_role accepte plusieurs rôles et retourne True si l'un correspond."""
        assert has_role(finance_user, 'admin', 'finance', 'secretariat') is True
    
    def test_has_role_admin_has_access_to_all(self, db, admin_user):
        """Un admin a accès à toutes les vues, même si son rôle n'est pas listé."""
        assert has_role(admin_user, 'finance') is True
        assert has_role(admin_user, 'secretariat') is True
        assert has_role(admin_user, 'responsable_club') is True
    
    def test_has_role_superuser_has_access_to_all(self, db, superuser):
        """Un superuser a accès à toutes les vues."""
        assert has_role(superuser, 'finance') is True
        assert has_role(superuser, 'admin') is True
        assert has_role(superuser, 'any_role') is True
    
    def test_has_role_anonymous_user_denied(self, db):
        """Un utilisateur anonyme n'a jamais accès."""
        anonymous = AnonymousUser()
        assert has_role(anonymous, 'membre') is False
        assert has_role(anonymous, 'admin') is False
    
    def test_has_role_none_user_denied(self, db):
        """Un utilisateur None n'a jamais accès."""
        assert has_role(None, 'membre') is False
    
    def test_has_role_with_empty_roles(self, db, admin_user):
        """has_role avec aucun rôle spécifié retourne True pour admin."""
        # Admin a toujours accès même sans rôles spécifiés
        assert has_role(admin_user) is True
    
    def test_has_role_membre_limited_access(self, db, membre_user):
        """Un membre n'a pas accès aux rôles privilégiés."""
        assert has_role(membre_user, 'admin') is False
        assert has_role(membre_user, 'finance') is False
        assert has_role(membre_user, 'secretariat') is False
        assert has_role(membre_user, 'membre') is True


# =============================================================================
# TESTS POUR get_user_permissions()
# =============================================================================

class TestGetUserPermissions:
    """Tests pour la fonction get_user_permissions()."""
    
    def test_get_permissions_admin(self, db, admin_user):
        """Un admin a accès à tous les modules et actions."""
        perms = get_user_permissions(admin_user)
        assert perms['modules'] == ['*']
        assert perms['actions'] == ['*']
    
    def test_get_permissions_superuser(self, db, superuser):
        """Un superuser a accès à tous les modules et actions."""
        perms = get_user_permissions(superuser)
        assert perms['modules'] == ['*']
        assert perms['actions'] == ['*']
    
    def test_get_permissions_finance(self, db, finance_user):
        """Un utilisateur finance a accès aux modules finance et campaigns."""
        perms = get_user_permissions(finance_user)
        assert 'finance' in perms['modules']
        assert 'campaigns' in perms['modules']
        assert 'validate' in perms['actions']
    
    def test_get_permissions_membre(self, db, membre_user):
        """Un membre a un accès limité."""
        perms = get_user_permissions(membre_user)
        assert 'members' in perms['modules']
        assert 'events' in perms['modules']
        assert 'view' in perms['actions']
        assert 'create' not in perms['actions']
    
    def test_get_permissions_anonymous(self, db):
        """Un utilisateur anonyme n'a aucune permission."""
        anonymous = AnonymousUser()
        perms = get_user_permissions(anonymous)
        assert perms['modules'] == []
        assert perms['actions'] == []
    
    def test_get_permissions_none_user(self, db):
        """Un utilisateur None n'a aucune permission."""
        perms = get_user_permissions(None)
        assert perms['modules'] == []
        assert perms['actions'] == []


# =============================================================================
# TESTS POUR @role_required DÉCORATEUR
# =============================================================================

class TestRoleRequiredDecorator:
    """Tests pour le décorateur @role_required."""
    
    @pytest.fixture
    def request_factory(self):
        return RequestFactory()
    
    @pytest.fixture
    def protected_view(self):
        """Vue protégée par @role_required('finance')."""
        @role_required('finance')
        def view(request):
            return HttpResponse('OK')
        return view
    
    @pytest.fixture
    def multi_role_view(self):
        """Vue protégée par plusieurs rôles."""
        @role_required('admin', 'finance', 'secretariat')
        def view(request):
            return HttpResponse('OK')
        return view
    
    def test_decorator_allows_matching_role(self, request_factory, protected_view, finance_user):
        """Le décorateur autorise un utilisateur avec le bon rôle."""
        request = request_factory.get('/test/')
        request.user = finance_user
        # Mock messages framework
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        response = protected_view(request)
        assert response.status_code == 200
        assert response.content == b'OK'
    
    def test_decorator_allows_admin(self, request_factory, protected_view, admin_user):
        """Le décorateur autorise toujours un admin."""
        request = request_factory.get('/test/')
        request.user = admin_user
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        response = protected_view(request)
        assert response.status_code == 200
    
    def test_decorator_allows_superuser(self, request_factory, protected_view, superuser):
        """Le décorateur autorise toujours un superuser."""
        request = request_factory.get('/test/')
        request.user = superuser
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        response = protected_view(request)
        assert response.status_code == 200
    
    def test_decorator_denies_wrong_role(self, request_factory, protected_view, membre_user):
        """Le décorateur refuse un utilisateur sans le bon rôle."""
        request = request_factory.get('/test/')
        request.user = membre_user
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        response = protected_view(request)
        # Devrait rediriger (302)
        assert response.status_code == 302
    
    def test_decorator_multi_role_allows_any(self, request_factory, multi_role_view, secretariat_user):
        """Le décorateur avec plusieurs rôles autorise si l'un correspond."""
        request = request_factory.get('/test/')
        request.user = secretariat_user
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        response = multi_role_view(request)
        assert response.status_code == 200


# =============================================================================
# TESTS POUR RoleRequiredMixin
# =============================================================================

class TestRoleRequiredMixin:
    """Tests pour le mixin RoleRequiredMixin."""
    
    @pytest.fixture
    def request_factory(self):
        return RequestFactory()
    
    @pytest.fixture
    def protected_view_class(self):
        """Vue CBV protégée par RoleRequiredMixin."""
        class ProtectedView(RoleRequiredMixin, View):
            allowed_roles = ('finance',)
            
            def get(self, request):
                return HttpResponse('OK')
        
        return ProtectedView
    
    @pytest.fixture
    def multi_role_view_class(self):
        """Vue CBV protégée par plusieurs rôles."""
        class MultiRoleView(RoleRequiredMixin, View):
            allowed_roles = ('admin', 'finance', 'secretariat')
            
            def get(self, request):
                return HttpResponse('OK')
        
        return MultiRoleView
    
    def test_mixin_allows_matching_role(self, request_factory, protected_view_class, finance_user):
        """Le mixin autorise un utilisateur avec le bon rôle."""
        request = request_factory.get('/test/')
        request.user = finance_user
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        view = protected_view_class.as_view()
        response = view(request)
        assert response.status_code == 200
    
    def test_mixin_allows_admin(self, request_factory, protected_view_class, admin_user):
        """Le mixin autorise toujours un admin."""
        request = request_factory.get('/test/')
        request.user = admin_user
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        view = protected_view_class.as_view()
        response = view(request)
        assert response.status_code == 200
    
    def test_mixin_denies_wrong_role(self, request_factory, protected_view_class, membre_user):
        """Le mixin refuse un utilisateur sans le bon rôle."""
        request = request_factory.get('/test/')
        request.user = membre_user
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        view = protected_view_class.as_view()
        response = view(request)
        # Devrait rediriger (302)
        assert response.status_code == 302
    
    def test_mixin_denies_anonymous(self, request_factory, protected_view_class):
        """Le mixin refuse un utilisateur anonyme."""
        request = request_factory.get('/test/')
        request.user = AnonymousUser()
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        view = protected_view_class.as_view()
        response = view(request)
        # Devrait rediriger vers login (302)
        assert response.status_code == 302


# =============================================================================
# PROPERTY-BASED TESTS
# =============================================================================

class TestPermissionEnforcementProperty:
    """
    Property 1: Permission Enforcement
    
    Pour tout utilisateur et toute combinaison de rôles requis,
    l'accès est accordé si et seulement si:
    - L'utilisateur est superuser, OU
    - L'utilisateur a le rôle 'admin', OU
    - L'utilisateur a l'un des rôles requis
    
    Validates: Requirements 2.1, 2.2, 2.3, 2.4
    """
    
    @pytest.mark.parametrize("user_role,required_roles,expected", [
        # Admin a toujours accès
        ('admin', ('finance',), True),
        ('admin', ('secretariat',), True),
        ('admin', ('membre',), True),
        
        # Finance a accès aux vues finance
        ('finance', ('finance',), True),
        ('finance', ('admin', 'finance'), True),
        ('finance', ('admin',), False),
        ('finance', ('secretariat',), False),
        
        # Secretariat a accès aux vues secretariat
        ('secretariat', ('secretariat',), True),
        ('secretariat', ('admin', 'secretariat'), True),
        ('secretariat', ('finance',), False),
        
        # Membre a accès limité
        ('membre', ('membre',), True),
        ('membre', ('admin',), False),
        ('membre', ('finance',), False),
        ('membre', ('secretariat',), False),
        
        # Responsable club
        ('responsable_club', ('responsable_club',), True),
        ('responsable_club', ('admin', 'responsable_club'), True),
        ('responsable_club', ('finance',), False),
        
        # Moniteur
        ('moniteur', ('moniteur',), True),
        ('moniteur', ('responsable_club',), False),
        
        # Encadrant
        ('encadrant', ('encadrant',), True),
        ('encadrant', ('admin', 'encadrant'), True),
        ('encadrant', ('finance',), False),
        
        # Responsable groupe
        ('responsable_groupe', ('responsable_groupe',), True),
        ('responsable_groupe', ('admin', 'responsable_groupe'), True),
        ('responsable_groupe', ('finance',), False),
    ])
    def test_permission_enforcement_property(self, db, user_role, required_roles, expected):
        """
        Property 1: Permission Enforcement
        
        Pour tout rôle utilisateur et toute combinaison de rôles requis,
        has_role retourne True si et seulement si l'utilisateur a l'un des rôles requis
        ou est admin.
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        """
        user = User.objects.create_user(
            username=f'test_{user_role}_{hash(required_roles)}',
            password='testpass123',
            role=user_role
        )
        
        result = has_role(user, *required_roles)
        assert result == expected, (
            f"has_role({user_role}, {required_roles}) devrait retourner {expected}, "
            f"mais a retourné {result}"
        )
    
    def test_superuser_always_has_access(self, db, superuser, all_roles):
        """
        Property: Un superuser a toujours accès, quel que soit le rôle requis.
        
        **Validates: Requirements 2.4**
        """
        for role in all_roles:
            assert has_role(superuser, role) is True, (
                f"Superuser devrait avoir accès au rôle {role}"
            )
    
    def test_admin_always_has_access(self, db, admin_user, all_roles):
        """
        Property: Un admin a toujours accès, quel que soit le rôle requis.
        
        **Validates: Requirements 2.4**
        """
        for role in all_roles:
            assert has_role(admin_user, role) is True, (
                f"Admin devrait avoir accès au rôle {role}"
            )
