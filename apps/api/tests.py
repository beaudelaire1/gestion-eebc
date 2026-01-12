"""
API Tests for EEBC Mobile App.

This module contains tests for all API endpoints to verify:
- Authentication (JWT login, refresh, logout, password change)
- Member directory endpoints
- Event endpoints
- Worship service endpoints
- Announcement endpoints
- Donation endpoints
- Profile endpoints
- Device registration endpoints
"""
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.members.models import Member
from apps.events.models import Event, EventRegistration
from apps.communication.models import Announcement
from apps.core.models import Site
from apps.api.models import DeviceToken, AnnouncementReadStatus


class AuthenticationAPITests(APITestCase):
    """Tests for authentication endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='membre'
        )
        self.login_url = reverse('api:token_obtain_pair')
        self.refresh_url = reverse('api:token_refresh')
        self.logout_url = reverse('api:logout')
        self.password_url = reverse('api:change_password')
    
    def test_login_success(self):
        """Test successful login returns JWT tokens."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])
        self.assertIn('user', response.data['data'])
        self.assertEqual(response.data['data']['user']['username'], 'testuser')
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns error."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])
    
    def test_login_must_change_password_flag(self):
        """Test login returns must_change_password flag when set."""
        self.user.must_change_password = True
        self.user.save()
        
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['data']['must_change_password'])
    
    def test_token_refresh(self):
        """Test token refresh returns new access token."""
        # First login to get tokens
        login_response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        refresh_token = login_response.data['data']['refresh']
        
        # Refresh the token
        response = self.client.post(self.refresh_url, {
            'refresh': refresh_token
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
    
    def test_logout(self):
        """Test logout blacklists refresh token."""
        # Login first
        login_response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        access_token = login_response.data['data']['access']
        refresh_token = login_response.data['data']['refresh']
        
        # Logout
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.post(self.logout_url, {
            'refresh': refresh_token
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
    
    def test_change_password(self):
        """Test password change endpoint."""
        # Login first
        login_response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        access_token = login_response.data['data']['access']
        
        # Change password
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.put(self.password_url, {
            'old_password': 'testpass123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify new password works
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass456'))
    
    def test_account_lockout_after_failed_attempts(self):
        """Test account gets locked after 5 failed login attempts."""
        for i in range(5):
            self.client.post(self.login_url, {
                'username': 'testuser',
                'password': 'wrongpassword'
            })
        
        # 6th attempt should show locked message
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_locked())


class MemberAPITests(APITestCase):
    """Tests for member directory endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='membre'
        )
        self.site = Site.objects.create(
            code='CAB',
            name='Cabassou',
            address='123 Test St'
        )
        self.member = Member.objects.create(
            first_name='Jean',
            last_name='Dupont',
            email='jean@example.com',
            phone='0594123456',
            status='actif',
            site=self.site
        )
        
        # Authenticate
        self.client = APIClient()
        login_response = self.client.post(reverse('api:token_obtain_pair'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.access_token = login_response.data['data']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_list_members(self):
        """Test listing members."""
        response = self.client.get(reverse('api:member-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_member_detail(self):
        """Test getting member detail."""
        response = self.client.get(
            reverse('api:member-detail', kwargs={'pk': self.member.pk})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Jean')
        self.assertEqual(response.data['last_name'], 'Dupont')
    
    def test_member_search(self):
        """Test searching members by name."""
        response = self.client.get(
            reverse('api:member-list'),
            {'search': 'Jean'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied."""
        self.client.credentials()  # Remove auth
        response = self.client.get(reverse('api:member-list'))
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class EventAPITests(APITestCase):
    """Tests for event endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='membre'
        )
        self.site = Site.objects.create(
            code='CAB',
            name='Cabassou'
        )
        self.event = Event.objects.create(
            title='Test Event',
            description='A test event',
            start_date=date.today() + timedelta(days=7),
            start_time='10:00:00',
            site=self.site
        )
        
        # Authenticate
        self.client = APIClient()
        login_response = self.client.post(reverse('api:token_obtain_pair'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.access_token = login_response.data['data']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_list_events(self):
        """Test listing events."""
        response = self.client.get(reverse('api:event-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_event_detail(self):
        """Test getting event detail."""
        response = self.client.get(
            reverse('api:event-detail', kwargs={'pk': self.event.pk})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Event')
    
    def test_event_registration(self):
        """Test registering for an event."""
        response = self.client.post(
            reverse('api:event_register', kwargs={'pk': self.event.pk})
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify registration exists
        self.assertTrue(
            EventRegistration.objects.filter(
                event=self.event,
                user=self.user
            ).exists()
        )
    
    def test_event_unregistration(self):
        """Test unregistering from an event."""
        # First register
        EventRegistration.objects.create(event=self.event, user=self.user)
        
        # Then unregister
        response = self.client.delete(
            reverse('api:event_register', kwargs={'pk': self.event.pk})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
    
    def test_my_registrations(self):
        """Test getting user's event registrations."""
        EventRegistration.objects.create(event=self.event, user=self.user)
        
        response = self.client.get(
            reverse('api:event-my-registrations')
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])


class AnnouncementAPITests(APITestCase):
    """Tests for announcement endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='membre'
        )
        self.announcement = Announcement.objects.create(
            title='Test Announcement',
            content='This is a test announcement',
            is_active=True,
            start_date=timezone.now() - timedelta(days=1),
            created_by=self.user
        )
        
        # Authenticate
        self.client = APIClient()
        login_response = self.client.post(reverse('api:token_obtain_pair'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.access_token = login_response.data['data']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_list_announcements(self):
        """Test listing announcements."""
        response = self.client.get(reverse('api:announcement-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_announcement_detail(self):
        """Test getting announcement detail."""
        response = self.client.get(
            reverse('api:announcement-detail', kwargs={'pk': self.announcement.pk})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Announcement')
    
    def test_mark_announcement_read(self):
        """Test marking announcement as read."""
        response = self.client.post(
            reverse('api:announcement-mark-read', kwargs={'pk': self.announcement.pk})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify read status exists
        self.assertTrue(
            AnnouncementReadStatus.objects.filter(
                user=self.user,
                announcement=self.announcement
            ).exists()
        )


class ProfileAPITests(APITestCase):
    """Tests for profile endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='membre'
        )
        
        # Authenticate
        self.client = APIClient()
        login_response = self.client.post(reverse('api:token_obtain_pair'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.access_token = login_response.data['data']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_get_profile(self):
        """Test getting user profile."""
        response = self.client.get(reverse('api:profile'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['username'], 'testuser')
        self.assertEqual(response.data['data']['email'], 'test@example.com')
    
    def test_update_profile(self):
        """Test updating user profile."""
        response = self.client.put(reverse('api:profile'), {
            'phone': '0594999999',
            'email': 'newemail@example.com'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify changes
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, '0594999999')
        self.assertEqual(self.user.email, 'newemail@example.com')


class DeviceRegistrationAPITests(APITestCase):
    """Tests for device registration endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='membre'
        )
        
        # Authenticate
        self.client = APIClient()
        login_response = self.client.post(reverse('api:token_obtain_pair'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.access_token = login_response.data['data']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_register_device(self):
        """Test registering a device token."""
        response = self.client.post(reverse('api:register_device'), {
            'token': 'test_fcm_token_12345',
            'platform': 'android',
            'device_name': 'Test Phone'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify device token exists
        self.assertTrue(
            DeviceToken.objects.filter(
                user=self.user,
                token='test_fcm_token_12345'
            ).exists()
        )
    
    def test_unregister_device(self):
        """Test unregistering a device token."""
        # First register
        DeviceToken.objects.create(
            user=self.user,
            token='test_fcm_token_12345',
            platform='android'
        )
        
        # Then unregister
        response = self.client.delete(reverse('api:register_device'), {
            'token': 'test_fcm_token_12345'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify device token is inactive
        device = DeviceToken.objects.get(token='test_fcm_token_12345')
        self.assertFalse(device.is_active)


class DonationAPITests(APITestCase):
    """Tests for donation endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='membre'
        )
        
        # Authenticate
        self.client = APIClient()
        login_response = self.client.post(reverse('api:token_obtain_pair'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.access_token = login_response.data['data']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_list_donations(self):
        """Test listing user's donations."""
        response = self.client.get(reverse('api:donation-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_list_tax_receipts(self):
        """Test listing user's tax receipts."""
        response = self.client.get(reverse('api:donation-receipts'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
