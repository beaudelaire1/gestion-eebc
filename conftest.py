"""
Fixtures partagées pour les tests pytest.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.test import RequestFactory

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Crée un utilisateur avec le rôle admin."""
    return User.objects.create_user(
        username='admin_test',
        password='testpass123',
        first_name='Admin',
        last_name='Test',
        role='admin'
    )


@pytest.fixture
def finance_user(db):
    """Crée un utilisateur avec le rôle finance."""
    return User.objects.create_user(
        username='finance_test',
        password='testpass123',
        first_name='Finance',
        last_name='Test',
        role='finance'
    )


@pytest.fixture
def secretariat_user(db):
    """Crée un utilisateur avec le rôle secretariat."""
    return User.objects.create_user(
        username='secretariat_test',
        password='testpass123',
        first_name='Secretariat',
        last_name='Test',
        role='secretariat'
    )


@pytest.fixture
def responsable_club_user(db):
    """Crée un utilisateur avec le rôle responsable_club."""
    return User.objects.create_user(
        username='responsable_club_test',
        password='testpass123',
        first_name='Responsable',
        last_name='Club',
        role='responsable_club'
    )


@pytest.fixture
def moniteur_user(db):
    """Crée un utilisateur avec le rôle moniteur."""
    return User.objects.create_user(
        username='moniteur_test',
        password='testpass123',
        first_name='Moniteur',
        last_name='Test',
        role='moniteur'
    )


@pytest.fixture
def membre_user(db):
    """Crée un utilisateur avec le rôle membre."""
    return User.objects.create_user(
        username='membre_test',
        password='testpass123',
        first_name='Membre',
        last_name='Test',
        role='membre'
    )


@pytest.fixture
def encadrant_user(db):
    """Crée un utilisateur avec le rôle encadrant."""
    return User.objects.create_user(
        username='encadrant_test',
        password='testpass123',
        first_name='Encadrant',
        last_name='Test',
        role='encadrant'
    )


@pytest.fixture
def responsable_groupe_user(db):
    """Crée un utilisateur avec le rôle responsable_groupe."""
    return User.objects.create_user(
        username='responsable_groupe_test',
        password='testpass123',
        first_name='Responsable',
        last_name='Groupe',
        role='responsable_groupe'
    )


@pytest.fixture
def superuser(db):
    """Crée un superuser."""
    return User.objects.create_superuser(
        username='superuser_test',
        password='testpass123',
        first_name='Super',
        last_name='User'
    )


@pytest.fixture
def authenticated_client(client, admin_user):
    """Client authentifié avec un utilisateur admin."""
    client.force_login(admin_user)
    return client


@pytest.fixture
def finance_client(client, finance_user):
    """Client authentifié avec un utilisateur finance."""
    client.force_login(finance_user)
    return client


@pytest.fixture
def membre_client(client, membre_user):
    """Client authentifié avec un utilisateur membre."""
    client.force_login(membre_user)
    return client


@pytest.fixture
def request_factory():
    """Factory pour créer des objets request."""
    return RequestFactory()


@pytest.fixture
def mock_request(request_factory, admin_user):
    """Request mock avec utilisateur authentifié et middleware."""
    request = request_factory.get('/')
    
    # Ajouter les middleware nécessaires
    SessionMiddleware(lambda x: None).process_request(request)
    request.session.save()
    
    AuthenticationMiddleware(lambda x: None).process_request(request)
    request.user = admin_user
    
    MessageMiddleware(lambda x: None).process_request(request)
    
    return request


@pytest.fixture
def all_roles():
    """Liste de tous les rôles disponibles."""
    return [
        'admin', 'secretariat', 'finance', 'responsable_club',
        'moniteur', 'responsable_groupe', 'encadrant', 'membre'
    ]


@pytest.fixture
def user_by_role(db):
    """Factory pour créer un utilisateur par rôle."""
    def _create_user(role):
        return User.objects.create_user(
            username=f'{role}_test_user',
            password='testpass123',
            first_name=role.title(),
            last_name='Test',
            role=role
        )
    return _create_user


@pytest.fixture
def client_by_role(client, user_by_role):
    """Factory pour créer un client authentifié par rôle."""
    def _create_client(role):
        user = user_by_role(role)
        client.force_login(user)
        return client, user
    return _create_client
