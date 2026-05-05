"""
Tests pour l'app transport — modèles DriverProfile, TransportRequest.
"""
import pytest
from datetime import date, time

from apps.accounts.models import User
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
