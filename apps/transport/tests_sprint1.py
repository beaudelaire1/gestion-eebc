"""
Tests Sprint 1 — Chauffeur Actions (Start/Arriving/Complete)
Objectif: 100% couverture des transitions de statut
"""
import pytest
from datetime import date, time
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import DriverProfile, TransportRequest, DriverLiveLocation

User = get_user_model()


@pytest.fixture
def driver_user():
    """Créer un utilisateur chauffeur."""
    user = User.objects.create_user(
        username='driver_test',
        email='driver@test.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def driver_profile(driver_user):
    """Créer un profil chauffeur."""
    return DriverProfile.objects.create(
        user=driver_user,
        vehicle_type='Minibus',
        capacity=8,
        is_available=True,
        available_sunday=True
    )


@pytest.fixture
def requester_user():
    """Créer un utilisateur demandeur."""
    return User.objects.create_user(
        username='requester_test',
        email='requester@test.com',
        password='testpass123'
    )


@pytest.mark.django_db
class TestTransportRequestStart:
    """Tests de l'action START (CONFIRMED → EN_ROUTE)."""
    
    def test_driver_can_start_confirmed_request(self, client, driver_profile):
        """Chauffeur peut démarrer un trajet confirmé."""
        req = TransportRequest.objects.create(
            requester_name='Alice Dupont',
            requester_phone='0694123456',
            pickup_address='15 rue Test',
            event_date=date.today(),
            event_time=time(10, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.CONFIRMED,
        )
        
        client.force_login(driver_profile.user)
        response = client.post(reverse('transport:request_start', args=[req.pk]))
        req.refresh_from_db()
        
        assert response.status_code == 302
        assert req.status == TransportRequest.Status.EN_ROUTE
        assert 'd\u00e9marr\u00e9' in response.wsgi_request._messages._store[0][0].message.lower()
    
    def test_driver_cannot_start_pending_request(self, client, driver_profile):
        """Chauffeur ne peut pas démarrer un trajet en attente."""
        req = TransportRequest.objects.create(
            requester_name='Bob Martin',
            requester_phone='0694654321',
            pickup_address='8 avenue Test',
            event_date=date.today(),
            event_time=time(11, 0),
            passengers_count=1,
            driver=driver_profile,
            status=TransportRequest.Status.PENDING,
        )
        
        client.force_login(driver_profile.user)
        response = client.post(reverse('transport:request_start', args=[req.pk]))
        req.refresh_from_db()
        
        assert response.status_code == 302
        assert req.status == TransportRequest.Status.PENDING  # Pas changé
    
    def test_driver_cannot_start_completed_request(self, client, driver_profile):
        """Chauffeur ne peut pas redémarrer un trajet complété."""
        req = TransportRequest.objects.create(
            requester_name='Charlie Durand',
            requester_phone='0694999999',
            pickup_address='5 place Test',
            event_date=date.today(),
            event_time=time(12, 0),
            passengers_count=3,
            driver=driver_profile,
            status=TransportRequest.Status.COMPLETED,
        )
        
        client.force_login(driver_profile.user)
        response = client.post(reverse('transport:request_start', args=[req.pk]))
        req.refresh_from_db()
        
        assert response.status_code == 302
        assert req.status == TransportRequest.Status.COMPLETED
    
    def test_only_assigned_driver_can_start(self, client, driver_profile, requester_user):
        """Seul le chauffeur assigné peut démarrer le trajet."""
        req = TransportRequest.objects.create(
            requester_name='Diana Test',
            requester_phone='0694111111',
            pickup_address='20 rue Test',
            event_date=date.today(),
            event_time=time(13, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.CONFIRMED,
        )
        
        client.force_login(requester_user)
        response = client.post(reverse('transport:request_start', args=[req.pk]))
        req.refresh_from_db()
        
        assert response.status_code == 302
        assert req.status == TransportRequest.Status.CONFIRMED  # Pas changé
        assert 'chauffeur assign' in response.wsgi_request._messages._store[0][0].message.lower()
    
    def test_unauthenticated_cannot_start(self, client):
        """Utilisateur non authentifié ne peut pas démarrer."""
        driver = User.objects.create_user(username='d', password='p')
        driver_profile = DriverProfile.objects.create(user=driver, vehicle_type='Car', capacity=4)
        req = TransportRequest.objects.create(
            requester_name='Test',
            requester_phone='0694',
            pickup_address='rue',
            event_date=date.today(),
            event_time=time(10, 0),
            driver=driver_profile,
            status=TransportRequest.Status.CONFIRMED,
        )
        
        response = client.post(reverse('transport:request_start', args=[req.pk]))
        assert response.status_code == 302  # Redirect to login


@pytest.mark.django_db
class TestTransportRequestArriving:
    """Tests de l'action ARRIVING (EN_ROUTE → ARRIVING)."""
    
    def test_driver_can_arriving_en_route_request(self, client, driver_profile):
        """Chauffeur peut signaler arrivée d'un trajet en route."""
        req = TransportRequest.objects.create(
            requester_name='Eve Rousseau',
            requester_phone='0694222222',
            pickup_address='25 rue Arriving',
            event_date=date.today(),
            event_time=time(14, 0),
            passengers_count=1,
            driver=driver_profile,
            status=TransportRequest.Status.EN_ROUTE,
        )
        
        client.force_login(driver_profile.user)
        response = client.post(reverse('transport:request_arriving', args=[req.pk]))
        req.refresh_from_db()
        
        assert response.status_code == 302
        assert req.status == TransportRequest.Status.ARRIVING
        assert 'arriv' in response.wsgi_request._messages._store[0][0].message.lower()
    
    def test_driver_cannot_arriving_confirmed_request(self, client, driver_profile):
        """Chauffeur ne peut pas signaler arrivée si pas en route."""
        req = TransportRequest.objects.create(
            requester_name='Frank Leblanc',
            requester_phone='0694333333',
            pickup_address='30 rue Nope',
            event_date=date.today(),
            event_time=time(15, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.CONFIRMED,
        )
        
        client.force_login(driver_profile.user)
        response = client.post(reverse('transport:request_arriving', args=[req.pk]))
        req.refresh_from_db()
        
        assert response.status_code == 302
        assert req.status == TransportRequest.Status.CONFIRMED  # Pas changé
    
    def test_only_assigned_driver_can_arriving(self, client, driver_profile, requester_user):
        """Seul le chauffeur assigné peut signaler arrivée."""
        req = TransportRequest.objects.create(
            requester_name='Grace Martin',
            requester_phone='0694444444',
            pickup_address='35 rue Grace',
            event_date=date.today(),
            event_time=time(16, 0),
            passengers_count=3,
            driver=driver_profile,
            status=TransportRequest.Status.EN_ROUTE,
        )
        
        client.force_login(requester_user)
        response = client.post(reverse('transport:request_arriving', args=[req.pk]))
        req.refresh_from_db()
        
        assert response.status_code == 302
        assert req.status == TransportRequest.Status.EN_ROUTE  # Pas changé


@pytest.mark.django_db
class TestTransportRequestComplete:
    """Tests de l'action COMPLETE (ARRIVING → COMPLETED ou EN_ROUTE → COMPLETED)."""
    
    def test_driver_can_complete_arriving_request(self, client, driver_profile):
        """Chauffeur peut compléter un trajet ARRIVING."""
        req = TransportRequest.objects.create(
            requester_name='Henry Dumont',
            requester_phone='0694555555',
            pickup_address='40 rue Complete',
            event_date=date.today(),
            event_time=time(17, 0),
            passengers_count=1,
            driver=driver_profile,
            status=TransportRequest.Status.ARRIVING,
        )
        
        client.force_login(driver_profile.user)
        response = client.post(reverse('transport:request_complete', args=[req.pk]))
        req.refresh_from_db()
        
        assert response.status_code == 302
        assert req.status == TransportRequest.Status.COMPLETED
        assert 'effectu' in response.wsgi_request._messages._store[0][0].message.lower()
    
    def test_driver_can_complete_en_route_request(self, client, driver_profile):
        """Chauffeur peut compléter directement un trajet EN_ROUTE (sans passer par ARRIVING)."""
        req = TransportRequest.objects.create(
            requester_name='Iris Laurent',
            requester_phone='0694666666',
            pickup_address='45 rue Route',
            event_date=date.today(),
            event_time=time(18, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.EN_ROUTE,
        )
        
        client.force_login(driver_profile.user)
        response = client.post(reverse('transport:request_complete', args=[req.pk]))
        req.refresh_from_db()
        
        assert response.status_code == 302
        assert req.status == TransportRequest.Status.COMPLETED
    
    def test_driver_cannot_complete_pending_request(self, client, driver_profile):
        """Chauffeur ne peut pas compléter un trajet en attente."""
        req = TransportRequest.objects.create(
            requester_name='Jack Petit',
            requester_phone='0694777777',
            pickup_address='50 rue Pending',
            event_date=date.today(),
            event_time=time(19, 0),
            passengers_count=1,
            driver=driver_profile,
            status=TransportRequest.Status.PENDING,
        )
        
        client.force_login(driver_profile.user)
        response = client.post(reverse('transport:request_complete', args=[req.pk]))
        req.refresh_from_db()
        
        assert response.status_code == 302
        assert req.status == TransportRequest.Status.PENDING  # Pas changé
    
    def test_only_assigned_driver_can_complete(self, client, driver_profile, requester_user):
        """Seul le chauffeur assigné peut compléter."""
        req = TransportRequest.objects.create(
            requester_name='Karen Dubois',
            requester_phone='0694888888',
            pickup_address='55 rue Karen',
            event_date=date.today(),
            event_time=time(20, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.ARRIVING,
        )
        
        client.force_login(requester_user)
        response = client.post(reverse('transport:request_complete', args=[req.pk]))
        req.refresh_from_db()
        
        assert response.status_code == 302
        assert req.status == TransportRequest.Status.ARRIVING  # Pas changé


@pytest.mark.django_db
class TestTransitionChains:
    """Tests de chaînes complètes de transitions."""
    
    def test_full_workflow_pending_to_completed(self, client, driver_profile):
        """Test du workflow complet: accepter → démarrer → arriver → compléter."""
        # 1. Créer demande en attente
        req = TransportRequest.objects.create(
            requester_name='Lewis Hamilton',
            requester_phone='0694999999',
            pickup_address='60 rue F1',
            event_date=date.today(),
            event_time=time(21, 0),
            passengers_count=1,
            status=TransportRequest.Status.PENDING,
        )
        
        # 2. Accepter (PENDING → CONFIRMED)
        client.force_login(driver_profile.user)
        response = client.post(reverse('transport:request_accept', args=[req.pk]))
        req.refresh_from_db()
        assert req.status == TransportRequest.Status.CONFIRMED
        assert req.driver_id == driver_profile.id
        
        # 3. Démarrer (CONFIRMED → EN_ROUTE)
        response = client.post(reverse('transport:request_start', args=[req.pk]))
        req.refresh_from_db()
        assert req.status == TransportRequest.Status.EN_ROUTE
        
        # 4. Arriver (EN_ROUTE → ARRIVING)
        response = client.post(reverse('transport:request_arriving', args=[req.pk]))
        req.refresh_from_db()
        assert req.status == TransportRequest.Status.ARRIVING
        
        # 5. Compléter (ARRIVING → COMPLETED)
        response = client.post(reverse('transport:request_complete', args=[req.pk]))
        req.refresh_from_db()
        assert req.status == TransportRequest.Status.COMPLETED
    
    def test_workflow_skip_arriving(self, client, driver_profile):
        """Test: accepter → démarrer → compléter (sans ARRIVING)."""
        req = TransportRequest.objects.create(
            requester_name='Max Verstappen',
            requester_phone='0694101010',
            pickup_address='65 rue F1',
            event_date=date.today(),
            event_time=time(22, 0),
            passengers_count=2,
            status=TransportRequest.Status.PENDING,
        )
        
        client.force_login(driver_profile.user)
        
        # Accepter
        client.post(reverse('transport:request_accept', args=[req.pk]))
        req.refresh_from_db()
        
        # Démarrer
        client.post(reverse('transport:request_start', args=[req.pk]))
        req.refresh_from_db()
        assert req.status == TransportRequest.Status.EN_ROUTE
        
        # Compléter directement (sans ARRIVING)
        response = client.post(reverse('transport:request_complete', args=[req.pk]))
        req.refresh_from_db()
        assert req.status == TransportRequest.Status.COMPLETED
