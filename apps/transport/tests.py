"""
Tests pour l'app transport — modèles DriverProfile, TransportRequest.
"""
import pytest
from datetime import date, time
from django.urls import reverse
from unittest.mock import patch

from apps.accounts.models import User
from apps.core.models import Family
from apps.members.models import Member
from apps.transport.models import DriverProfile, TransportRequest, DriverLiveLocation


@pytest.fixture
def driver_user(db):
    return User.objects.create_user(
        username='driver', email='driver@example.com',
        password='Pass123!', role='chauffeur',
    )


@pytest.fixture
def driver_profile(db, driver_user):
    return DriverProfile.objects.create(
        user=driver_user,
        vehicle_type='minibus',
        vehicle_model='Toyota HiAce',
        license_plate='GF-123-AB',
        capacity=12,
        is_available=True,
    )


@pytest.mark.django_db
class TestDriverProfile:

    def test_create_driver(self, driver_profile):
        assert driver_profile.pk is not None
        assert str(driver_profile)
        assert driver_profile.capacity == 12

    def test_driver_availability(self, driver_profile):
        assert driver_profile.is_available is True


@pytest.mark.django_db
class TestTransportRequest:

    def test_create_request(self, driver_profile):
        req = TransportRequest.objects.create(
            requester_name='Marie Duval',
            requester_phone='0694555666',
            pickup_address='12 rue de Cayenne',
            event_date=date.today(),
            event_time=time(9, 0),
            event_name='Culte dimanche',
            passengers_count=4,
            driver=driver_profile,
            status='pending',
        )
        assert req.pk is not None
        assert str(req)

    def test_request_without_driver(self):
        req = TransportRequest.objects.create(
            requester_name='Jean Martin',
            requester_phone='0694111222',
            pickup_address='8 avenue Voltaire',
            event_date=date.today(),
            event_time=time(9, 0),
            passengers_count=2,
            status='pending',
        )
        assert req.driver is None


@pytest.mark.django_db
class TestDriverLiveLocation:

    def test_create_live_location(self, driver_profile):
        req = TransportRequest.objects.create(
            requester_name='Pauline Test',
            requester_phone='0694000000',
            pickup_address='15 rue des Fleurs',
            event_date=date.today(),
            event_time=time(10, 30),
            passengers_count=1,
            driver=driver_profile,
            status='confirmed',
        )
        live = DriverLiveLocation.objects.create(
            transport_request=req,
            driver=driver_profile,
            latitude='4.922500',
            longitude='-52.305800',
            is_active=True,
        )

        assert live.pk is not None
        assert live.transport_request == req
        assert live.driver == driver_profile


@pytest.mark.django_db
class TestTransportRequestPermissions:

    def test_request_detail_redirects_unrelated_user(self, client, driver_profile):
        requester_user = User.objects.create_user(
            username='requester',
            email='requester@example.com',
            password='Pass123!',
            role='membre',
        )
        requester_member = Member.objects.create(
            first_name='Pauline',
            last_name='Requester',
            user=requester_user,
        )
        intruder = User.objects.create_user(
            username='intruder',
            email='intruder@example.com',
            password='Pass123!',
            role='membre',
        )
        req = TransportRequest.objects.create(
            requester_member=requester_member,
            requester_name='Pauline Requester',
            requester_phone='0694001234',
            pickup_address='12 rue Test',
            event_date=date.today(),
            event_time=time(9, 0),
            passengers_count=2,
            driver=driver_profile,
            status='confirmed',
        )

        client.force_login(intruder)
        response = client.get(reverse('transport:request_detail', args=[req.pk]))

        assert response.status_code == 302
        assert response.url == reverse('transport:requests')

    def test_requests_list_only_shows_user_requests(self, client, driver_profile):
        requester_user = User.objects.create_user(
            username='member-list',
            email='member-list@example.com',
            password='Pass123!',
            role='membre',
        )
        requester_member = Member.objects.create(
            first_name='Marie',
            last_name='Liste',
            user=requester_user,
        )
        TransportRequest.objects.create(
            requester_member=requester_member,
            requester_name='Marie Liste',
            requester_phone='0694001111',
            pickup_address='10 rue visible',
            event_date=date.today(),
            event_time=time(8, 0),
            passengers_count=1,
            status='pending',
        )
        TransportRequest.objects.create(
            requester_name='Autre Personne',
            requester_phone='0694002222',
            pickup_address='11 rue cachee',
            event_date=date.today(),
            event_time=time(10, 0),
            passengers_count=3,
            driver=driver_profile,
            status='confirmed',
        )

        client.force_login(requester_user)
        response = client.get(reverse('transport:requests'))

        assert response.status_code == 200
        page_requests = list(response.context['page_obj'].object_list)
        assert len(page_requests) == 1
        assert page_requests[0].requester_name == 'Marie Liste'

    def test_requests_list_exposes_live_tracking_link_for_assigned_driver(self, client, driver_profile):
        requester_user = User.objects.create_user(
            username='member-live',
            email='member-live@example.com',
            password='Pass123!',
            role='membre',
        )
        requester_member = Member.objects.create(
            first_name='Claire',
            last_name='Suivi',
            user=requester_user,
        )
        req = TransportRequest.objects.create(
            requester_member=requester_member,
            requester_name='Claire Suivi',
            requester_phone='0694003333',
            pickup_address='15 rue arrivée',
            event_date=date.today(),
            event_time=time(11, 0),
            passengers_count=2,
            driver=driver_profile,
            status='confirmed',
        )

        client.force_login(requester_user)
        response = client.get(reverse('transport:requests'))
        response_html = response.content.decode()

        assert response.status_code == 200
        assert response.context['page_obj'].object_list[0].pk == req.pk
        assert reverse('transport:request_detail', args=[req.pk]) in response_html
        assert 'Suivre l\'arrivée' in response_html

    def test_driver_list_links_back_to_transport_requests(self, client):
        manager = User.objects.create_user(
            username='transport-manager',
            email='transport-manager@example.com',
            password='Pass123!',
            role='secretariat',
        )

        client.force_login(manager)
        response = client.get(reverse('transport:drivers'))
        response_html = response.content.decode()

        assert response.status_code == 200
        assert reverse('transport:requests') in response_html
        assert 'Demandes transport' in response_html

    def test_requests_scope_tracking_filters_on_confirmed_assigned_requests(self, client, driver_profile):
        manager = User.objects.create_user(
            username='tracking-manager',
            email='tracking-manager@example.com',
            password='Pass123!',
            role='secretariat',
        )
        tracked_request = TransportRequest.objects.create(
            requester_name='Paul Tracking',
            requester_phone='0694111000',
            pickup_address='1 rue live',
            event_date=date.today(),
            event_time=time(9, 0),
            passengers_count=1,
            driver=driver_profile,
            status='confirmed',
        )
        TransportRequest.objects.create(
            requester_name='Pending Sans Chauffeur',
            requester_phone='0694111001',
            pickup_address='2 rue pending',
            event_date=date.today(),
            event_time=time(10, 0),
            passengers_count=2,
            status='pending',
        )

        client.force_login(manager)
        response = client.get(reverse('transport:requests'), {'scope': 'tracking'})

        assert response.status_code == 200
        page_requests = list(response.context['page_obj'].object_list)
        assert [item.pk for item in page_requests] == [tracked_request.pk]
        assert response.context['transport_scope'] == 'tracking'

    def test_sidebar_exposes_transport_tool_links(self, client):
        manager = User.objects.create_user(
            username='sidebar-manager',
            email='sidebar-manager@example.com',
            password='Pass123!',
            role='secretariat',
        )

        client.force_login(manager)
        response = client.get(reverse('transport:requests'))
        response_html = response.content.decode()

        assert response.status_code == 200
        assert reverse('transport:request_create') in response_html
        assert f"{reverse('transport:requests')}?scope=tracking" in response_html
        assert f"{reverse('transport:requests')}?scope=arrivals" in response_html
        assert f"{reverse('transport:requests')}?scope=pending" in response_html
        assert reverse('transport:calendar') in response_html
        assert reverse('transport:drivers') in response_html
        assert reverse('transport:driver_create') in response_html

    def test_live_status_includes_waiting_person_location_and_eta(self, client, driver_profile):
        requester_user = User.objects.create_user(
            username='eta-member',
            email='eta-member@example.com',
            password='Pass123!',
            role='membre',
        )
        family = Family.objects.create(
            name='Famille ETA',
            address='15 rue ETA',
            latitude='4.932500',
            longitude='-52.305800',
        )
        requester_member = Member.objects.create(
            first_name='Alice',
            last_name='Attente',
            user=requester_user,
            family=family,
        )
        req = TransportRequest.objects.create(
            requester_member=requester_member,
            requester_name='Alice Attente',
            requester_phone='0694004444',
            pickup_address='15 rue ETA',
            event_date=date.today(),
            event_time=time(11, 30),
            passengers_count=1,
            driver=driver_profile,
            status='confirmed',
        )
        DriverLiveLocation.objects.create(
            transport_request=req,
            driver=driver_profile,
            latitude='4.922500',
            longitude='-52.305800',
            speed_kmh='30.00',
            is_active=True,
        )

        client.force_login(requester_user)
        response = client.get(reverse('transport:live_status', args=[req.pk]))
        data = response.json()

        assert response.status_code == 200
        assert data['pickup_location']['has_location'] is True
        assert data['pickup_location']['label'] == 'Alice Attente'
        assert data['eta_available'] is True
        assert data['eta_minutes'] >= 1
        assert data['eta_mode'] == 'vitesse_live'
        assert data['distance_to_pickup_km'] is not None

    def test_live_status_does_not_geocode_on_poll_without_cache(self, client, driver_profile):
        requester_user = User.objects.create_user(
            username='poll-member',
            email='poll-member@example.com',
            password='Pass123!',
            role='membre',
        )
        requester_member = Member.objects.create(
            first_name='Paul',
            last_name='Polling',
            user=requester_user,
        )
        req = TransportRequest.objects.create(
            requester_member=requester_member,
            requester_name='Paul Polling',
            requester_phone='0694005555',
            pickup_address='99 route sans cache',
            event_date=date.today(),
            event_time=time(12, 0),
            passengers_count=1,
            driver=driver_profile,
            status='confirmed',
        )
        DriverLiveLocation.objects.create(
            transport_request=req,
            driver=driver_profile,
            latitude='4.922500',
            longitude='-52.305800',
            is_active=True,
        )

        client.force_login(requester_user)
        with patch('apps.transport.views.geocode_address_with_metadata') as mock_geocode:
            response = client.get(reverse('transport:live_status', args=[req.pk]))

        assert response.status_code == 200
        assert response.json()['pickup_location']['has_location'] is False
        mock_geocode.assert_not_called()

    def test_requester_can_set_gps_pickup_location_without_driver_position(self, client, driver_profile):
        requester_user = User.objects.create_user(
            username='gps-member',
            email='gps-member@example.com',
            password='Pass123!',
            role='membre',
        )
        requester_member = Member.objects.create(
            first_name='Nadia',
            last_name='GPS',
            user=requester_user,
        )
        req = TransportRequest.objects.create(
            requester_member=requester_member,
            requester_name='Nadia GPS',
            requester_phone='0694006666',
            pickup_address='4 rue GPS',
            event_date=date.today(),
            event_time=time(13, 0),
            passengers_count=1,
            driver=driver_profile,
            status='confirmed',
        )

        client.force_login(requester_user)
        response = client.post(
            reverse('transport:pickup_location_update', args=[req.pk]),
            data='{"source":"gps","latitude":4.9325,"longitude":-52.3158}',
            content_type='application/json',
        )
        data = response.json()

        assert response.status_code == 200
        assert data['has_location'] is False
        assert data['pickup_location']['has_location'] is True
        assert data['pickup_location']['source'] == 'requester_gps'
        assert data['pickup_location']['source_label'] == 'GPS du demandeur'
        assert data['eta_label'] == 'En attente du signal GPS'

    def test_pickup_location_can_switch_back_to_postal_address(self, client, driver_profile):
        requester_user = User.objects.create_user(
            username='address-member',
            email='address-member@example.com',
            password='Pass123!',
            role='membre',
        )
        family = Family.objects.create(
            name='Famille Adresse',
            address='8 rue Adresse',
            latitude='4.942500',
            longitude='-52.325800',
        )
        requester_member = Member.objects.create(
            first_name='Lina',
            last_name='Adresse',
            user=requester_user,
            family=family,
        )
        req = TransportRequest.objects.create(
            requester_member=requester_member,
            requester_name='Lina Adresse',
            requester_phone='0694007777',
            pickup_address='8 rue Adresse',
            pickup_latitude='4.900000',
            pickup_longitude='-52.300000',
            pickup_location_source=TransportRequest.PickupLocationSource.REQUESTER_GPS,
            event_date=date.today(),
            event_time=time(14, 0),
            passengers_count=1,
            driver=driver_profile,
            status='confirmed',
        )

        client.force_login(requester_user)
        response = client.post(
            reverse('transport:pickup_location_update', args=[req.pk]),
            data='{"source":"address"}',
            content_type='application/json',
        )
        data = response.json()
        req.refresh_from_db()

        assert response.status_code == 200
        assert req.pickup_latitude is None
        assert req.pickup_longitude is None
        assert req.pickup_location_source == TransportRequest.PickupLocationSource.POSTAL_ADDRESS
        assert data['pickup_location']['has_location'] is True
        assert data['pickup_location']['source'] == 'postal_address'
        assert data['pickup_location']['source_label'] == 'Adresse postale'

    def test_request_detail_exposes_pickup_location_choices(self, client, driver_profile):
        requester_user = User.objects.create_user(
            username='choice-member',
            email='choice-member@example.com',
            password='Pass123!',
            role='membre',
        )
        requester_member = Member.objects.create(
            first_name='Chloe',
            last_name='Choix',
            user=requester_user,
        )
        req = TransportRequest.objects.create(
            requester_member=requester_member,
            requester_name='Chloe Choix',
            requester_phone='0694008888',
            pickup_address='2 rue Choix',
            event_date=date.today(),
            event_time=time(15, 0),
            passengers_count=1,
            driver=driver_profile,
            status='confirmed',
        )

        client.force_login(requester_user)
        with patch('apps.transport.views.geocode_address_with_metadata') as mock_geocode:
            mock_geocode.return_value = {'coords': None, 'provider': 'nominatim', 'from_cache': False}
            response = client.get(reverse('transport:request_detail', args=[req.pk]))
        response_html = response.content.decode()

        assert response.status_code == 200
        assert 'Position et arrî' in response_html or 'Position et arrivée' in response_html
        assert 'pickupEmptyState' in response_html
        assert 'transport-live-icon--waiting' in response_html
        assert 'GPS actuel' in response_html
        assert 'Adresse postale' in response_html
        assert reverse('transport:pickup_location_update', args=[req.pk]) in response_html

    def test_driver_can_view_pending_unassigned_request(self, client, driver_profile):
        req = TransportRequest.objects.create(
            requester_name='Anne Attente',
            requester_phone='0694010101',
            pickup_address='10 rue Acceptation',
            event_date=date.today(),
            event_time=time(9, 30),
            passengers_count=1,
            status='pending',
        )

        client.force_login(driver_profile.user)
        response = client.get(reverse('transport:request_detail', args=[req.pk]))
        response_html = response.content.decode()

        assert response.status_code == 200
        assert 'Accepter cette demande' in response_html
        assert reverse('transport:request_accept', args=[req.pk]) in response_html

    def test_driver_can_accept_pending_unassigned_request(self, client, driver_profile):
        req = TransportRequest.objects.create(
            requester_name='Bruno Acceptation',
            requester_phone='0694010202',
            pickup_address='12 rue Acceptation',
            event_date=date.today(),
            event_time=time(10, 0),
            passengers_count=2,
            status='pending',
        )

        client.force_login(driver_profile.user)
        response = client.post(reverse('transport:request_accept', args=[req.pk]))
        req.refresh_from_db()

        assert response.status_code == 302
        assert response.url == reverse('transport:request_detail', args=[req.pk])
        assert req.driver_id == driver_profile.pk
        assert req.status == TransportRequest.Status.CONFIRMED

    def test_non_driver_user_cannot_accept_request(self, client):
        member_user = User.objects.create_user(
            username='not-driver',
            email='not-driver@example.com',
            password='Pass123!',
            role='membre',
        )
        req = TransportRequest.objects.create(
            requester_name='Carla Demande',
            requester_phone='0694010303',
            pickup_address='14 rue Acceptation',
            event_date=date.today(),
            event_time=time(11, 0),
            passengers_count=1,
            status='pending',
        )

        client.force_login(member_user)
        response = client.post(reverse('transport:request_accept', args=[req.pk]))
        req.refresh_from_db()

        assert response.status_code == 302
        assert req.driver_id is None
        assert req.status == 'pending'

    def test_driver_sees_available_scope_in_requests_list(self, client, driver_profile):
        TransportRequest.objects.create(
            requester_name='Diane Dispo',
            requester_phone='0694010404',
            pickup_address='16 rue Dispo',
            event_date=date.today(),
            event_time=time(12, 0),
            passengers_count=1,
            status='pending',
        )

        client.force_login(driver_profile.user)
        response = client.get(reverse('transport:requests'), {'scope': 'available'})
        response_html = response.content.decode()

        assert response.status_code == 200
        assert 'Demandes disponibles' in response_html
        assert 'Diane Dispo' in response_html
