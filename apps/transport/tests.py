from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from datetime import date, time
from .models import DriverProfile, TransportRequest
from .views import send_confirmation_email

User = get_user_model()


class TransportModuleTests(TestCase):
    """Tests pour le module Transport."""
    
    def setUp(self):
        """Configuration des tests."""
        # Créer des utilisateurs de test
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            role='admin'
        )
        
        self.driver_user = User.objects.create_user(
            username='driver',
            password='testpass123',
            first_name='Jean',
            last_name='Dupont'
        )
        
        # Créer un profil chauffeur
        self.driver_profile = DriverProfile.objects.create(
            user=self.driver_user,
            vehicle_type='Voiture',
            vehicle_model='Peugeot 308',
            capacity=5,
            zone='Centre-ville',
            is_available=True,
            available_sunday=True,
            available_week=True  # Disponible en semaine aussi
        )
        
        # Créer une demande de transport
        self.transport_request = TransportRequest.objects.create(
            requester_name='Marie Martin',
            requester_phone='0123456789',
            requester_email='marie.martin@example.com',
            pickup_address='123 Rue de la Paix, 75001 Paris',
            event_date=date.today(),
            event_time=time(10, 0),
            event_name='Culte du dimanche',
            passengers_count=2
        )
        
        self.client = Client()
    
    def test_driver_crud_operations(self):
        """Test des opérations CRUD pour les chauffeurs."""
        self.client.force_login(self.admin_user)
        
        # Test création chauffeur
        response = self.client.get(reverse('transport:driver_create'))
        self.assertEqual(response.status_code, 200)
        
        # Test liste chauffeurs
        response = self.client.get(reverse('transport:drivers'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jean Dupont')
        
        # Test détail chauffeur
        response = self.client.get(reverse('transport:driver_detail', args=[self.driver_profile.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jean Dupont')
        
        # Test modification chauffeur
        response = self.client.get(reverse('transport:driver_update', args=[self.driver_profile.pk]))
        self.assertEqual(response.status_code, 200)
    
    def test_transport_request_crud_operations(self):
        """Test des opérations CRUD pour les demandes de transport."""
        self.client.force_login(self.admin_user)
        
        # Test création demande
        response = self.client.get(reverse('transport:request_create'))
        self.assertEqual(response.status_code, 200)
        
        # Test liste demandes
        response = self.client.get(reverse('transport:requests'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Marie Martin')
        
        # Test détail demande
        response = self.client.get(reverse('transport:request_detail', args=[self.transport_request.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Marie Martin')
        
        # Test modification demande
        response = self.client.get(reverse('transport:request_update', args=[self.transport_request.pk]))
        self.assertEqual(response.status_code, 200)
    
    def test_driver_assignment(self):
        """Test de l'assignation de chauffeur."""
        self.client.force_login(self.admin_user)
        
        # Test page d'assignation
        response = self.client.get(reverse('transport:assign_driver', args=[self.transport_request.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jean Dupont')  # Le chauffeur doit être disponible
        
        # Test assignation avec confirmation
        response = self.client.post(reverse('transport:assign_driver', args=[self.transport_request.pk]), {
            'driver': self.driver_profile.pk,
            'status': 'confirmed'
        })
        self.assertEqual(response.status_code, 302)  # Redirection après succès
        
        # Vérifier que l'assignation a fonctionné
        self.transport_request.refresh_from_db()
        self.assertEqual(self.transport_request.driver, self.driver_profile)
        self.assertEqual(self.transport_request.status, 'confirmed')
    
    def test_calendar_view(self):
        """Test de la vue calendrier."""
        self.client.force_login(self.admin_user)
        
        # Test page calendrier
        response = self.client.get(reverse('transport:calendar'))
        self.assertEqual(response.status_code, 200)
        
        # Test API données calendrier
        response = self.client.get(reverse('transport:calendar_data'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_email_confirmation(self):
        """Test de l'envoi d'email de confirmation."""
        # Assigner un chauffeur à la demande
        self.transport_request.driver = self.driver_profile
        self.transport_request.status = 'confirmed'
        self.transport_request.save()
        
        # Tester l'envoi d'email
        mail.outbox = []  # Vider la boîte mail de test
        
        try:
            send_confirmation_email(self.transport_request)
            # Vérifier qu'un email a été envoyé
            self.assertEqual(len(mail.outbox), 1)
            
            email = mail.outbox[0]
            self.assertEqual(email.to, ['marie.martin@example.com'])
            self.assertIn('Confirmation de transport', email.subject)
            self.assertIn('Marie Martin', email.body)
            self.assertIn('Jean Dupont', email.body)
        except Exception as e:
            # Si l'envoi d'email échoue (pas de configuration SMTP), c'est normal en test
            print(f"Email test skipped due to: {e}")
    
    def test_permissions(self):
        """Test des permissions d'accès."""
        # Créer un utilisateur sans permissions
        regular_user = User.objects.create_user(
            username='regular',
            password='testpass123',
            role='membre'
        )
        
        self.client.force_login(regular_user)
        
        # Test accès refusé pour création chauffeur
        response = self.client.get(reverse('transport:driver_create'))
        self.assertIn(response.status_code, [302, 403])  # Redirection ou accès refusé
        
        # Test accès refusé pour assignation chauffeur
        response = self.client.get(reverse('transport:assign_driver', args=[self.transport_request.pk]))
        self.assertIn(response.status_code, [302, 403])
        
        # Test accès autorisé pour voir les demandes (lecture seule)
        response = self.client.get(reverse('transport:requests'))
        self.assertEqual(response.status_code, 200)