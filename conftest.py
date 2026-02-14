"""
Fixtures pytest pour les tests EEBC.
À utiliser dans tous les tests avec: pytest
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from apps.core.models import Site
from apps.members.models import Member
from apps.events.models import Event, EventCategory
from apps.finance.models import FinancialTransaction, DonationCategory
from apps.bibleclub.models import Child, AgeGroup
from test_factories import (
    UserFactory,
    SiteFactory,
    MemberFactory,
    EventFactory,
    FinancialTransactionFactory,
)

User = get_user_model()


# ==================================================================================
# FIXTURES - Sites
# ==================================================================================

@pytest.fixture
def site_cayenne(db):
    """Site Cayenne."""
    return SiteFactory(name="Cayenne", city="Cayenne")


@pytest.fixture
def site_remire(db):
    """Site Remire."""
    return SiteFactory(name="Remire-Montjoly", city="Remire-Montjoly")


@pytest.fixture
def sites(site_cayenne, site_remire):
    """Tous les sites."""
    return [site_cayenne, site_remire]


# ==================================================================================
# FIXTURES - Utilisateurs et rôles
# ==================================================================================

@pytest.fixture
def admin_user(db):
    """Utilisateur admin."""
    return UserFactory(is_staff=True, is_superuser=True, role="admin")


@pytest.fixture
def pastor_user(db):
    """Utilisateur pasteur."""
    return UserFactory(role="pasteur")


@pytest.fixture
def secretary_user(db):
    """Utilisateur secrétaire."""
    return UserFactory(role="secretariat")


@pytest.fixture
def member_user(db):
    """Utilisateur simple membre."""
    return UserFactory(role="membre")


@pytest.fixture
def users(admin_user, pastor_user, secretary_user, member_user):
    """Tous les utilisateurs de test."""
    return {
        'admin': admin_user,
        'pastor': pastor_user,
        'secretary': secretary_user,
        'member': member_user,
    }


# ==================================================================================
# FIXTURES - Membres
# ==================================================================================

@pytest.fixture
def member(db, site_cayenne):
    """Membre simple."""
    return MemberFactory(site=site_cayenne, status='actif')


@pytest.fixture
def members(db, site_cayenne, site_remire):
    """Plusieurs membres."""
    members_cayenne = MemberFactory.create_batch(10, site=site_cayenne, status='actif')
    members_remire = MemberFactory.create_batch(5, site=site_remire, status='actif')
    return members_cayenne + members_remire


@pytest.fixture
def inactive_member(db, site_cayenne):
    """Membre inactif."""
    return MemberFactory(site=site_cayenne, status='inactif')


# ==================================================================================
# FIXTURES - Événements
# ==================================================================================

@pytest.fixture
def event_category(db):
    """Catégorie d'événement."""
    return EventCategory.objects.create(name="Culte", color="#0066cc")


@pytest.fixture
def event(db, site_cayenne, event_category, pastor_user):
    """Événement simple."""
    event = EventFactory(site=site_cayenne, category=event_category)
    event.organizers.add(pastor_user)
    return event


@pytest.fixture
def events(db, site_cayenne, event_category, pastor_user):
    """Plusieurs événements."""
    events = []
    for i in range(5):
        event = EventFactory(site=site_cayenne, category=event_category)
        event.organizers.add(pastor_user)
        events.append(event)
    return events


# ==================================================================================
# FIXTURES - Finance
# ==================================================================================

@pytest.fixture
def donation_category(db):
    """Catégorie de don."""
    return DonationCategory.objects.create(name="Dîme", color="#28a745")


@pytest.fixture
def financial_transaction(db, site_cayenne, donation_category):
    """Transaction financière."""
    return FinancialTransactionFactory(
        site=site_cayenne,
        category=donation_category,
        status='validated'
    )


@pytest.fixture
def financial_transactions(db, site_cayenne, donation_category):
    """Plusieurs transactions."""
    return FinancialTransactionFactory.create_batch(
        10,
        site=site_cayenne,
        category=donation_category,
        status='validated'
    )


# ==================================================================================
# FIXTURES - Bible Club
# ==================================================================================

@pytest.fixture
def age_group(db):
    """Groupe d'âge."""
    return AgeGroup.objects.create(name="6-8 ans", min_age=6, max_age=8)


@pytest.fixture
def child(db, member, age_group):
    """Enfant simple."""
    return Child.objects.create(
        member=member,
        age_group=age_group,
        status='active',
    )


# ==================================================================================
# FIXTURES - HTTP Client
# ==================================================================================

@pytest.fixture
def client():
    """Client Django test."""
    return Client()


@pytest.fixture
def authenticated_client(client, admin_user):
    """Client authentifié en tant qu'admin."""
    client.force_login(admin_user)
    return client


# ==================================================================================
# FIXTURES - Données complètes
# ==================================================================================

@pytest.fixture
def complete_setup(db, sites, users, members, events, financial_transactions):
    """Configuration complète pour les tests intégration."""
    return {
        'sites': sites,
        'users': users,
        'members': members,
        'events': events,
        'transactions': financial_transactions,
    }


# ==================================================================================
# FIXTURES - Marqueurs personnalisés
# ==================================================================================

@pytest.fixture
def django_db_setup(django_db_blocker, django_db_usefitures):
    """Configuration BD pour les tests."""
    with django_db_blocker.unblock():
        from django.core.management import call_command
        # Créer les sites par défaut
        Site.objects.get_or_create(name="Cayenne", defaults={'city': 'Cayenne'})
        Site.objects.get_or_create(name="Remire-Montjoly", defaults={'city': 'Remire-Montjoly'})
