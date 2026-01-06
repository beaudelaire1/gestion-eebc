"""
Tests de sécurité pour les vues pastorales des membres.

Vérifie que les vues pastorales (événements de vie, visites) sont protégées
par les rôles appropriés selon les requirements 27.1, 27.2, 27.3.
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.members.models import Member, LifeEvent, VisitationLog

User = get_user_model()


@pytest.fixture
def member(db):
    """Créer un membre de test."""
    return Member.objects.create(
        first_name="Jean",
        last_name="Dupont",
        email="jean.dupont@example.com",
        status="actif"
    )


@pytest.fixture
def life_event(db, member, admin_user):
    """Créer un événement de vie de test."""
    return LifeEvent.objects.create(
        title="Naissance",
        event_type="naissance",
        event_date="2024-01-01",
        primary_member=member,
        recorded_by=admin_user
    )


@pytest.fixture
def visit(db, member, admin_user):
    """Créer une visite de test."""
    return VisitationLog.objects.create(
        member=member,
        visitor=admin_user,
        visit_type="domicile",
        status="planifie",
        scheduled_date="2024-01-15"
    )


class TestPastoralViewsProtection:
    """Tests de protection des vues pastorales."""
    
    def test_life_event_list_requires_pastoral_role(self, client, membre_user):
        """Test que la liste des événements de vie nécessite un rôle pastoral."""
        client.force_login(membre_user)
        response = client.get(reverse('members:life_events'))
        
        # Doit être redirigé car le rôle 'membre' n'a pas accès
        assert response.status_code == 302
    
    def test_life_event_list_allows_admin(self, client, admin_user):
        """Test que les admins peuvent accéder aux événements de vie."""
        client.force_login(admin_user)
        response = client.get(reverse('members:life_events'))
        
        assert response.status_code == 200
    
    def test_life_event_list_allows_secretariat(self, client, secretariat_user):
        """Test que le secrétariat peut accéder aux événements de vie."""
        client.force_login(secretariat_user)
        response = client.get(reverse('members:life_events'))
        
        assert response.status_code == 200
    
    def test_life_event_list_allows_encadrant(self, client, encadrant_user):
        """Test que les encadrants peuvent accéder aux événements de vie."""
        client.force_login(encadrant_user)
        response = client.get(reverse('members:life_events'))
        
        assert response.status_code == 200
    
    def test_life_event_create_requires_pastoral_role(self, client, membre_user):
        """Test que la création d'événement de vie nécessite un rôle pastoral."""
        client.force_login(membre_user)
        response = client.get(reverse('members:life_event_create'))
        
        assert response.status_code == 302
    
    def test_visit_list_requires_pastoral_role(self, client, membre_user):
        """Test que la liste des visites nécessite un rôle pastoral."""
        client.force_login(membre_user)
        response = client.get(reverse('members:visits'))
        
        assert response.status_code == 302
    
    def test_visit_create_requires_pastoral_role(self, client, membre_user):
        """Test que la création de visite nécessite un rôle pastoral."""
        client.force_login(membre_user)
        response = client.get(reverse('members:visit_create'))
        
        assert response.status_code == 302
    
    def test_kanban_board_requires_pastoral_role(self, client, membre_user):
        """Test que le tableau Kanban nécessite un rôle pastoral."""
        client.force_login(membre_user)
        response = client.get(reverse('members:kanban'))
        
        assert response.status_code == 302
    
    def test_kanban_board_allows_pastoral_roles(self, client, admin_user, secretariat_user, encadrant_user):
        """Test que les rôles pastoraux peuvent accéder au Kanban."""
        for user in [admin_user, secretariat_user, encadrant_user]:
            client.force_login(user)
            response = client.get(reverse('members:kanban'))
            assert response.status_code == 200


class TestMemberListReadAccess:
    """Tests d'accès en lecture à la liste des membres."""
    
    def test_member_list_allows_all_authenticated_users(self, client, membre_user, admin_user, secretariat_user):
        """Test que tous les utilisateurs authentifiés peuvent voir la liste des membres."""
        for user in [membre_user, admin_user, secretariat_user]:
            client.force_login(user)
            response = client.get(reverse('members:list'))
            assert response.status_code == 200
    
    def test_member_detail_allows_all_authenticated_users(self, client, member, membre_user, admin_user):
        """Test que tous les utilisateurs authentifiés peuvent voir les détails d'un membre."""
        for user in [membre_user, admin_user]:
            client.force_login(user)
            response = client.get(reverse('members:detail', kwargs={'pk': member.pk}))
            assert response.status_code == 200
    
    def test_member_detail_hides_pastoral_data_for_regular_users(self, client, member, membre_user, life_event, visit):
        """Test que les données pastorales sont cachées aux utilisateurs normaux."""
        client.force_login(membre_user)
        response = client.get(reverse('members:detail', kwargs={'pk': member.pk}))
        
        assert response.status_code == 200
        assert 'can_view_pastoral_data' not in response.context
        assert 'life_events' not in response.context
        assert 'visits' not in response.context
    
    def test_member_detail_shows_pastoral_data_for_pastoral_roles(self, client, member, admin_user, life_event, visit):
        """Test que les données pastorales sont visibles pour les rôles pastoraux."""
        client.force_login(admin_user)
        response = client.get(reverse('members:detail', kwargs={'pk': member.pk}))
        
        assert response.status_code == 200
        assert response.context['can_view_pastoral_data'] is True
        assert 'life_events' in response.context
        assert 'visits' in response.context


class TestPastoralDataAccess:
    """Tests d'accès aux données pastorales spécifiques."""
    
    def test_life_event_detail_requires_pastoral_role(self, client, life_event, membre_user):
        """Test que le détail d'un événement de vie nécessite un rôle pastoral."""
        client.force_login(membre_user)
        response = client.get(reverse('members:life_event_detail', kwargs={'pk': life_event.pk}))
        
        assert response.status_code == 302
    
    def test_visit_detail_requires_pastoral_role(self, client, visit, membre_user):
        """Test que le détail d'une visite nécessite un rôle pastoral."""
        client.force_login(membre_user)
        response = client.get(reverse('members:visit_detail', kwargs={'pk': visit.pk}))
        
        assert response.status_code == 302
    
    def test_members_needing_visit_requires_pastoral_role(self, client, membre_user):
        """Test que la liste des membres nécessitant une visite nécessite un rôle pastoral."""
        client.force_login(membre_user)
        response = client.get(reverse('members:members_needing_visit'))
        
        assert response.status_code == 302


@pytest.mark.parametrize("role,should_have_access", [
    ('admin', True),
    ('secretariat', True), 
    ('encadrant', True),
    ('finance', False),
    ('responsable_club', False),
    ('moniteur', False),
    ('responsable_groupe', False),
    ('membre', False),
])
def test_pastoral_access_by_role(client, db, role, should_have_access):
    """Test paramétré pour vérifier l'accès pastoral par rôle."""
    user = User.objects.create_user(
        username=f'test_{role}',
        password='testpass123',
        role=role
    )
    
    client.force_login(user)
    response = client.get(reverse('members:life_events'))
    
    if should_have_access:
        assert response.status_code == 200
    else:
        assert response.status_code == 302  # Redirection car accès refusé