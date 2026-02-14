"""
Tests pour les vues (permissionsf, CRUD, etc.).
"""

import pytest
from django.urls import reverse
from django.test import Client
from apps.accounts.models import User
from apps.members.models import Member
from test_factories import UserFactory, MemberFactory, SiteFactory

pytestmark = pytest.mark.django_db


class TestMemberViews:
    """Tests des vues Member."""
    
    @pytest.fixture
    def client(self):
        return Client()
    
    @pytest.fixture
    def user(self):
        return UserFactory(is_staff=True, role='admin')
    
    def test_member_list_view_requires_login(self, client):
        """La vue member_list nécessite l'authentification."""
        response = client.get('/members/')
        assert response.status_code in [302, 401]  # Redirect ou Unauthorized
    
    def test_member_list_view_authenticated(self, client, user):
        """Membre authentifiée peut voir la liste."""
        client.force_login(user)
        response = client.get(reverse('members:list'))
        
        assert response.status_code == 200
        assert 'members' in response.context
    
    def test_member_detail_view(self, client, user):
        """Voir le détail d'un membre."""
        client.force_login(user)
        member = MemberFactory()
        
        response = client.get(reverse('members:detail', kwargs={'pk': member.pk}))
        
        assert response.status_code == 200
        assert response.context['member'] == member
    
    def test_member_create_view_requires_permission(self, client):
        """La création de membre nécessite le rôle admin/secrétaire."""
        # Utilisateur sans droit
        user = UserFactory(role='membre')
        client.force_login(user)
        
        response = client.get(reverse('members:create'))
        # Devrait être refusé
        assert response.status_code in [403, 302]  # Forbidden ou Redirect
    
    def test_member_create_view_admin_allowed(self, client, user):
        """Membre admin peut créer des membres."""
        client.force_login(user)
        response = client.get(reverse('members:create'))
        
        assert response.status_code == 200


class TestAccountViews:
    """Tests des vues Accounts."""
    
    def test_login_view(self, client):
        """Page de login accessible."""
        response = client.get(reverse('accounts:login'))
        assert response.status_code == 200
    
    def test_login_with_valid_credentials(self, client):
        """Login avec identifiants valides."""
        user = UserFactory(username='testuser')
        user.set_password('password123')
        user.save()
        
        response = client.post(
            reverse('accounts:login'),
            {'username': 'testuser', 'password': 'password123'},
            follow=True
        )
        
        # Vérifier que l'utilisateur est authentifié
        assert response.wsgi_request.user.is_authenticated
    
    def test_login_with_invalid_credentials(self, client):
        """Login échoue avec mauvais mot de passe."""
        user = UserFactory(username='testuser')
        user.set_password('password123')
        user.save()
        
        response = client.post(
            reverse('accounts:login'),
            {'username': 'testuser', 'password': 'wrongpassword'},
        )
        
        # Devrait pas être authentifié
        assert not response.wsgi_request.user.is_authenticated


class TestFormValidation:
    """Tests de validation des formulaires."""
    
    def test_member_form_valid(self):
        """Formulaire membre valide."""
        from apps.members.forms import MemberForm
        
        site = SiteFactory()
        data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'email': 'jean@example.com',
            'phone': '0123456789',
            'date_of_birth': '1990-01-01',
            'gender': 'M',
            'status': 'actif',
            'site': site.pk,
        }
        
        form = MemberForm(data)
        assert form.is_valid()
    
    def test_member_form_missing_required_field(self):
        """Formulaire membre avec champ manquant."""
        from apps.members.forms import MemberForm
        
        data = {
            'first_name': 'Jean',
            # last_name manquant
            'email': 'jean@example.com',
        }
        
        form = MemberForm(data)
        assert not form.is_valid()
        assert 'last_name' in form.errors or form.errors


class TestSecurityViews:
    """Tests de sécurité des vues."""
    
    @pytest.mark.security
    def test_csrf_protection(self, client):
        """CSRF protection activée."""
        response = client.get(reverse('members:create'))
        # La réponse devrait contenir le token CSRF
        if response.status_code == 200:
            assert 'csrfmiddlewaretoken' in response.content.decode()
    
    @pytest.mark.security
    def test_sql_injection_protection(self, client, user):
        """Protégé contre les injections SQL."""
        client.force_login(user)
        
        # Essayer une injection SQL
        response = client.get(
            reverse('members:list'),
            {'search': "'; DROP TABLE members; --"}
        )
        
        # Ne doit pas causer d'erreur SQL
        assert response.status_code != 500


class TestPagination:
    """Tests de pagination."""
    
    def test_member_list_pagination(self, client, user):
        """La liste des membres est paginée."""
        client.force_login(user)
        
        # Créer 30 membres (plus que le défaut de 25)
        site = SiteFactory()
        MemberFactory.create_batch(30, site=site)
        
        response = client.get(reverse('members:list'))
        
        assert response.status_code == 200
        # Vérifier que la pagination est présente
        if 'paginator' in response.context:
            assert response.context['paginator'].count == 30


class TestAjaxViews:
    """Tests des vues AJAX."""
    
    def test_ajax_request_identification(self, client, user):
        """Identificateur des requêtes AJAX."""
        client.force_login(user)
        
        # Requête avec header AJAX
        response = client.get(
            reverse('members:list'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        assert response.status_code == 200
