"""
Tests Sprint 3 — API Publique Tracking (sans authentification)
Objectif: Vérifier que le lien public fonctionne correctement
"""
import pytest
from datetime import date, time
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
import json

from .models import DriverProfile, TransportRequest, DriverLiveLocation

User = get_user_model()


@pytest.fixture
def driver_user():
    """Créer un utilisateur chauffeur."""
    user = User.objects.create_user(
        username='driver_public',
        email='driver_public@test.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def driver_profile(driver_user):
    """Créer un profil chauffeur."""
    return DriverProfile.objects.create(
        user=driver_user,
        vehicle_type='Minibus',
        vehicle_model='Toyota Hiace',
        capacity=8,
        is_available=True,
        available_sunday=True
    )


@pytest.mark.django_db
class TestPublicTrackingAPI:
    """Tests de l'API JSON publique."""
    
    def test_invalid_token_returns_404(self, client):
        """Token invalide retourne 404."""
        response = client.get(
            reverse('transport:public_track_api', args=['invalid-token-xyz'])
        )
        assert response.status_code == 404
        data = json.loads(response.content)
        assert 'error' in data
    
    def test_pending_request_cannot_be_tracked(self, client, driver_profile):
        """Demande PENDING ne peut pas être tracée."""
        req = TransportRequest.objects.create(
            requester_name='Alice Public',
            requester_phone='0694123456',
            requester_email='alice@test.com',
            pickup_address='15 rue Public',
            event_date=date.today(),
            event_time=time(10, 0),
            passengers_count=2,
            status=TransportRequest.Status.PENDING,
        )
        
        response = client.get(
            reverse('transport:public_track_api', args=[str(req.tracking_token)])
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['can_track'] is False
        assert data['status'] == 'pending'
    
    def test_confirmed_request_can_be_tracked(self, client, driver_profile):
        """Demande CONFIRMED peut être tracée."""
        req = TransportRequest.objects.create(
            requester_name='Bob Public',
            requester_phone='0694654321',
            requester_email='bob@test.com',
            pickup_address='8 avenue Public',
            event_date=date.today(),
            event_time=time(11, 0),
            passengers_count=1,
            driver=driver_profile,
            status=TransportRequest.Status.CONFIRMED,
        )
        
        response = client.get(
            reverse('transport:public_track_api', args=[str(req.tracking_token)])
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['can_track'] is True
        assert data['status'] == 'confirmed'
        assert data['driver'] is not None
        assert data['driver']['name'] == driver_profile.user.get_full_name()
    
    def test_en_route_request_returns_driver_info(self, client, driver_profile):
        """Demande EN_ROUTE affiche infos chauffeur."""
        req = TransportRequest.objects.create(
            requester_name='Charlie Public',
            requester_phone='0694999999',
            requester_email='charlie@test.com',
            pickup_address='5 place Public',
            event_date=date.today(),
            event_time=time(12, 0),
            passengers_count=3,
            driver=driver_profile,
            status=TransportRequest.Status.EN_ROUTE,
        )
        
        response = client.get(
            reverse('transport:public_track_api', args=[str(req.tracking_token)])
        )
        data = json.loads(response.content)
        
        assert data['driver'] is not None
        assert data['driver']['vehicle']['type'] == 'Minibus'
        assert data['driver']['vehicle']['capacity'] == 8
    
    def test_en_route_with_live_location(self, client, driver_profile):
        """Demande EN_ROUTE avec position live."""
        req = TransportRequest.objects.create(
            requester_name='Diana Public',
            requester_phone='0694111111',
            requester_email='diana@test.com',
            pickup_address='20 rue Public',
            event_date=date.today(),
            event_time=time(13, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.EN_ROUTE,
        )
        
        # Créer position live
        live = DriverLiveLocation.objects.create(
            transport_request=req,
            driver=driver_profile,
            latitude=Decimal('4.922500'),
            longitude=Decimal('-52.305800'),
            speed_kmh=Decimal('45.5'),
            accuracy_m=Decimal('10.5'),
            heading_deg=Decimal('180.0'),
            is_active=True,
        )
        
        response = client.get(
            reverse('transport:public_track_api', args=[str(req.tracking_token)])
        )
        data = json.loads(response.content)
        
        assert data['position'] is not None
        assert abs(data['position']['latitude'] - 4.922500) < 0.001
        assert abs(data['position']['longitude'] - (-52.305800)) < 0.001
        assert data['position']['speed_kmh'] == 45.5
        assert data['position']['accuracy_m'] == 10.5
    
    def test_completed_request_cannot_be_tracked(self, client, driver_profile):
        """Demande COMPLETED ne peut pas être tracée."""
        req = TransportRequest.objects.create(
            requester_name='Edward Public',
            requester_phone='0694222222',
            requester_email='edward@test.com',
            pickup_address='25 rue Public',
            event_date=date.today(),
            event_time=time(14, 0),
            passengers_count=1,
            driver=driver_profile,
            status=TransportRequest.Status.COMPLETED,
        )
        
        response = client.get(
            reverse('transport:public_track_api', args=[str(req.tracking_token)])
        )
        data = json.loads(response.content)
        
        assert data['can_track'] is False
        assert data['status'] == 'completed'
    
    def test_no_authentication_required(self, client, driver_profile):
        """Pas d'authentification requise pour l'API."""
        req = TransportRequest.objects.create(
            requester_name='Frank Public',
            requester_phone='0694333333',
            requester_email='frank@test.com',
            pickup_address='30 rue Public',
            event_date=date.today(),
            event_time=time(15, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.EN_ROUTE,
        )
        
        # Client non authentifié doit pouvoir accéder
        response = client.get(
            reverse('transport:public_track_api', args=[str(req.tracking_token)])
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestPublicTrackingPage:
    """Tests de la page HTML publique."""
    
    def test_invalid_token_returns_error_page(self, client):
        """Token invalide affiche page d'erreur."""
        response = client.get(
            reverse('transport:public_track', args=['invalid-token'])
        )
        assert response.status_code == 404
        assert 'expiré' in response.content.decode().lower()
    
    def test_pending_request_page_no_tracking(self, client):
        """Page PENDING n'affiche pas de suivi."""
        req = TransportRequest.objects.create(
            requester_name='Grace Page',
            requester_phone='0694444444',
            requester_email='grace@test.com',
            pickup_address='35 rue Page',
            event_date=date.today(),
            event_time=time(16, 0),
            passengers_count=1,
            status=TransportRequest.Status.PENDING,
        )
        
        response = client.get(
            reverse('transport:public_track', args=[str(req.tracking_token)])
        )
        assert response.status_code == 200
        html = response.content.decode()
        assert 'Suivi de votre trajet' in html
    
    def test_en_route_page_shows_map(self, client, driver_profile):
        """Page EN_ROUTE affiche la carte Leaflet."""
        req = TransportRequest.objects.create(
            requester_name='Henry Page',
            requester_phone='0694555555',
            requester_email='henry@test.com',
            pickup_address='40 rue Page',
            event_date=date.today(),
            event_time=time(17, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.EN_ROUTE,
        )
        
        response = client.get(
            reverse('transport:public_track', args=[str(req.tracking_token)])
        )
        assert response.status_code == 200
        html = response.content.decode()
        
        # Vérifier présence des éléments clés
        assert 'Leaflet' in html
        assert '<div id="map"></div>' in html
        assert req.requester_name in html
        assert 'Votre chauffeur' in html
    
    def test_page_includes_driver_info(self, client, driver_profile):
        """Page affiche infos chauffeur."""
        req = TransportRequest.objects.create(
            requester_name='Iris Page',
            requester_phone='0694666666',
            requester_email='iris@test.com',
            pickup_address='45 rue Page',
            event_date=date.today(),
            event_time=time(18, 0),
            passengers_count=3,
            driver=driver_profile,
            status=TransportRequest.Status.CONFIRMED,
        )
        
        response = client.get(
            reverse('transport:public_track', args=[str(req.tracking_token)])
        )
        html = response.content.decode()
        
        assert driver_profile.user.get_full_name() in html
        assert driver_profile.vehicle_type in html
    
    def test_page_includes_pickup_address(self, client):
        """Page affiche l'adresse de prise en charge."""
        req = TransportRequest.objects.create(
            requester_name='Jack Page',
            requester_phone='0694777777',
            requester_email='jack@test.com',
            pickup_address='50 rue Page, Cayenne',
            event_date=date.today(),
            event_time=time(19, 0),
            passengers_count=1,
            status=TransportRequest.Status.PENDING,
        )
        
        response = client.get(
            reverse('transport:public_track', args=[str(req.tracking_token)])
        )
        html = response.content.decode()
        
        assert '50 rue Page, Cayenne' in html
    
    def test_page_polling_script_included(self, client, driver_profile):
        """Page inclut le script de polling auto."""
        req = TransportRequest.objects.create(
            requester_name='Karen Page',
            requester_phone='0694888888',
            requester_email='karen@test.com',
            pickup_address='55 rue Page',
            event_date=date.today(),
            event_time=time(20, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.EN_ROUTE,
        )
        
        response = client.get(
            reverse('transport:public_track', args=[str(req.tracking_token)])
        )
        html = response.content.decode()
        
        # Vérifier présence du script de polling
        assert 'setInterval' in html
        assert 'updateTracking' in html
        assert '5000' in html  # 5 secondes
    
    def test_page_no_authentication_required(self, client):
        """Page accessible sans authentification."""
        req = TransportRequest.objects.create(
            requester_name='Leo NoAuth',
            requester_phone='0694999999',
            requester_email='leo@test.com',
            pickup_address='60 rue NoAuth',
            event_date=date.today(),
            event_time=time(21, 0),
            passengers_count=1,
            status=TransportRequest.Status.PENDING,
        )
        
        # Client non authentifié
        response = client.get(
            reverse('transport:public_track', args=[str(req.tracking_token)])
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestTrackingTokenUniqueness:
    """Tests que chaque demande a un token unique."""
    
    def test_tracking_token_generated_on_creation(self):
        """Token généré automatiquement."""
        req = TransportRequest.objects.create(
            requester_name='Token Test',
            requester_phone='0694000000',
            requester_email='token@test.com',
            pickup_address='65 rue Token',
            event_date=date.today(),
            event_time=time(22, 0),
            passengers_count=1,
            status=TransportRequest.Status.PENDING,
        )
        
        assert req.tracking_token is not None
        assert len(str(req.tracking_token)) > 0
    
    def test_tracking_tokens_are_unique(self):
        """Chaque demande a un token unique."""
        req1 = TransportRequest.objects.create(
            requester_name='Token1',
            requester_phone='0694111111',
            requester_email='token1@test.com',
            pickup_address='70 rue Token1',
            event_date=date.today(),
            event_time=time(22, 0),
            passengers_count=1,
            status=TransportRequest.Status.PENDING,
        )
        
        req2 = TransportRequest.objects.create(
            requester_name='Token2',
            requester_phone='0694222222',
            requester_email='token2@test.com',
            pickup_address='71 rue Token2',
            event_date=date.today(),
            event_time=time(22, 0),
            passengers_count=1,
            status=TransportRequest.Status.PENDING,
        )
        
        assert req1.tracking_token != req2.tracking_token
