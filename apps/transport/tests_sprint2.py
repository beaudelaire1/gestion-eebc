"""
Tests Sprint 2 — Notifications Passager
Objectif: Vérifier que les notifications sont envoyées aux bons moments
"""
import pytest
from datetime import date, time
from unittest.mock import patch, MagicMock
from django.core.mail import send_mail
from django.contrib.auth import get_user_model

from .models import DriverProfile, TransportRequest
from .notifications import (
    send_driver_accepted_notification,
    send_driver_en_route_notification,
    send_driver_arriving_notification,
    send_driver_completed_notification,
)

User = get_user_model()


@pytest.fixture
def driver_user():
    """Créer un utilisateur chauffeur."""
    user = User.objects.create_user(
        username='driver_sprint2',
        email='driver_sprint2@test.com',
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
class TestNotificationFunctions:
    """Tests des fonctions de notification directes."""
    
    @patch('apps.transport.notifications.send_mail')
    def test_send_driver_accepted_notification(self, mock_send_mail, driver_profile):
        """Test envoi notification acceptation."""
        req = TransportRequest.objects.create(
            requester_name='Alice Transport',
            requester_phone='0694123456',
            requester_email='alice@test.com',
            pickup_address='15 rue Test',
            event_date=date.today(),
            event_time=time(10, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.CONFIRMED,
        )
        
        send_driver_accepted_notification(req)
        
        assert mock_send_mail.called
        call_args = mock_send_mail.call_args
        assert 'alice@test.com' in call_args[1]['recipient_list']
        assert 'confirmé' in call_args[1]['subject'].lower()
    
    @patch('apps.transport.notifications.send_mail')
    def test_send_driver_en_route_notification(self, mock_send_mail, driver_profile):
        """Test envoi notification en route."""
        req = TransportRequest.objects.create(
            requester_name='Bob Transport',
            requester_phone='0694654321',
            requester_email='bob@test.com',
            pickup_address='8 avenue Test',
            event_date=date.today(),
            event_time=time(11, 0),
            passengers_count=1,
            driver=driver_profile,
            status=TransportRequest.Status.EN_ROUTE,
        )
        
        send_driver_en_route_notification(req)
        
        assert mock_send_mail.called
        call_args = mock_send_mail.call_args
        assert 'bob@test.com' in call_args[1]['recipient_list']
        assert 'route' in call_args[1]['subject'].lower()
    
    @patch('apps.transport.notifications.send_mail')
    def test_send_driver_arriving_notification(self, mock_send_mail, driver_profile):
        """Test envoi notification arrivée."""
        req = TransportRequest.objects.create(
            requester_name='Charlie Transport',
            requester_phone='0694999999',
            requester_email='charlie@test.com',
            pickup_address='5 place Test',
            event_date=date.today(),
            event_time=time(12, 0),
            passengers_count=3,
            driver=driver_profile,
            status=TransportRequest.Status.ARRIVING,
        )
        
        send_driver_arriving_notification(req)
        
        assert mock_send_mail.called
        call_args = mock_send_mail.call_args
        assert 'charlie@test.com' in call_args[1]['recipient_list']
        assert 'bient' in call_args[1]['subject'].lower() or 'arrive' in call_args[1]['subject'].lower()
    
    @patch('apps.transport.notifications.send_mail')
    def test_send_driver_completed_notification(self, mock_send_mail, driver_profile):
        """Test envoi notification complété."""
        req = TransportRequest.objects.create(
            requester_name='Diana Transport',
            requester_phone='0694111111',
            requester_email='diana@test.com',
            pickup_address='20 rue Test',
            event_date=date.today(),
            event_time=time(13, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.COMPLETED,
        )
        
        send_driver_completed_notification(req)
        
        assert mock_send_mail.called
        call_args = mock_send_mail.call_args
        assert 'diana@test.com' in call_args[1]['recipient_list']
        assert 'effectu' in call_args[1]['subject'].lower()
    
    @patch('apps.transport.notifications.send_mail')
    def test_no_email_for_requester(self, mock_send_mail, driver_profile):
        """Test: pas d'email si le demandeur n'en a pas."""
        req = TransportRequest.objects.create(
            requester_name='Edward Transport',
            requester_phone='0694222222',
            requester_email='',  # Pas d'email
            pickup_address='25 rue Test',
            event_date=date.today(),
            event_time=time(14, 0),
            passengers_count=1,
            driver=driver_profile,
            status=TransportRequest.Status.CONFIRMED,
        )
        
        send_driver_accepted_notification(req)
        
        # Pas d'appel send_mail
        assert not mock_send_mail.called


@pytest.mark.django_db
class TestSignalNotifications:
    """Tests des notifications via signaux Django."""
    
    @patch('apps.transport.notifications.send_driver_accepted_notification')
    def test_signal_sends_notification_on_accept(self, mock_notify, driver_profile):
        """Test: signal déclenche notification quand chauffeur accepte."""
        req = TransportRequest.objects.create(
            requester_name='Frank Signal',
            requester_phone='0694333333',
            requester_email='frank@test.com',
            pickup_address='30 rue Signal',
            event_date=date.today(),
            event_time=time(15, 0),
            passengers_count=2,
            status=TransportRequest.Status.PENDING,
        )
        
        # Chauffeur accepte (change status PENDING → CONFIRMED)
        req.driver = driver_profile
        req.status = TransportRequest.Status.CONFIRMED
        req.save()
        
        # Le signal doit avoir appelé la fonction de notification
        assert mock_notify.called
    
    @patch('apps.transport.notifications.send_driver_en_route_notification')
    def test_signal_sends_notification_on_start(self, mock_notify, driver_profile):
        """Test: signal déclenche notification quand chauffeur démarre."""
        req = TransportRequest.objects.create(
            requester_name='Grace Signal',
            requester_phone='0694444444',
            requester_email='grace@test.com',
            pickup_address='35 rue Signal',
            event_date=date.today(),
            event_time=time(16, 0),
            passengers_count=1,
            driver=driver_profile,
            status=TransportRequest.Status.CONFIRMED,
        )
        
        # Chauffeur démarre (change status CONFIRMED → EN_ROUTE)
        req.status = TransportRequest.Status.EN_ROUTE
        req.save()
        
        assert mock_notify.called
    
    @patch('apps.transport.notifications.send_driver_arriving_notification')
    def test_signal_sends_notification_on_arriving(self, mock_notify, driver_profile):
        """Test: signal déclenche notification quand chauffeur arrive."""
        req = TransportRequest.objects.create(
            requester_name='Henry Signal',
            requester_phone='0694555555',
            requester_email='henry@test.com',
            pickup_address='40 rue Signal',
            event_date=date.today(),
            event_time=time(17, 0),
            passengers_count=3,
            driver=driver_profile,
            status=TransportRequest.Status.EN_ROUTE,
        )
        
        # Chauffeur signale arrivée (EN_ROUTE → ARRIVING)
        req.status = TransportRequest.Status.ARRIVING
        req.save()
        
        assert mock_notify.called
    
    @patch('apps.transport.notifications.send_driver_completed_notification')
    def test_signal_sends_notification_on_complete(self, mock_notify, driver_profile):
        """Test: signal déclenche notification quand trajet complet."""
        req = TransportRequest.objects.create(
            requester_name='Iris Signal',
            requester_phone='0694666666',
            requester_email='iris@test.com',
            pickup_address='45 rue Signal',
            event_date=date.today(),
            event_time=time(18, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.ARRIVING,
        )
        
        # Chauffeur complète (ARRIVING → COMPLETED)
        req.status = TransportRequest.Status.COMPLETED
        req.save()
        
        assert mock_notify.called
    
    @patch('apps.transport.notifications.send_driver_accepted_notification')
    def test_signal_no_notification_on_creation(self, mock_notify):
        """Test: pas de notification à la création (avant acceptation)."""
        # Créer une demande (ne déclenche pas le signal)
        TransportRequest.objects.create(
            requester_name='Jack Creation',
            requester_phone='0694777777',
            requester_email='jack@test.com',
            pickup_address='50 rue Creation',
            event_date=date.today(),
            event_time=time(19, 0),
            passengers_count=1,
            status=TransportRequest.Status.PENDING,
        )
        
        # Pas d'appel de notification
        assert not mock_notify.called
    
    @patch('apps.transport.notifications.send_driver_accepted_notification')
    def test_signal_no_notification_on_same_status(self, mock_notify, driver_profile):
        """Test: pas de notification si status ne change pas."""
        req = TransportRequest.objects.create(
            requester_name='Karen Update',
            requester_phone='0694888888',
            requester_email='karen@test.com',
            pickup_address='55 rue Update',
            event_date=date.today(),
            event_time=time(20, 0),
            passengers_count=2,
            driver=driver_profile,
            status=TransportRequest.Status.CONFIRMED,
        )
        
        # Sauvegarder sans changer le status (met à jour created_at, etc)
        req.notes = "Updated notes"
        req.save()
        
        # Pas d'appel de notification
        assert not mock_notify.called
