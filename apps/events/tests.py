"""
Tests pour le module Events CRUD.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date, time
from .models import Event, EventCategory
from .forms import EventForm, EventCancelForm, EventDuplicateForm

User = get_user_model()


class EventCRUDTestCase(TestCase):
    """Tests pour les opérations CRUD des événements."""
    
    def setUp(self):
        """Configuration des tests."""
        # Créer des utilisateurs de test
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        
        self.secretariat_user = User.objects.create_user(
            username='secretariat_test',
            email='secretariat@test.com',
            password='testpass123',
            role='secretariat'
        )
        
        self.membre_user = User.objects.create_user(
            username='membre_test',
            email='membre@test.com',
            password='testpass123',
            role='membre'
        )
        
        # Créer une catégorie de test
        self.category = EventCategory.objects.create(
            name='Test Category',
            color='#ff0000'
        )
        
        # Créer un événement de test
        self.event = Event.objects.create(
            title='Test Event',
            description='Test description',
            start_date=date.today(),
            start_time=time(14, 0),
            location='Test Location',
            category=self.category
        )
        self.event.organizers.add(self.admin_user)
        
        self.client = Client()
    
    def test_event_create_view_requires_permission(self):
        """Test que la création d'événement nécessite les bonnes permissions."""
        # Test sans authentification
        response = self.client.get(reverse('events:create'))
        self.assertEqual(response.status_code, 302)  # Redirection vers login
        
        # Test avec utilisateur membre (pas autorisé)
        self.client.login(username='membre_test', password='testpass123')
        response = self.client.get(reverse('events:create'))
        self.assertEqual(response.status_code, 302)  # Redirection (accès refusé)
        
        # Test avec utilisateur admin (autorisé)
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(reverse('events:create'))
        self.assertEqual(response.status_code, 200)
        
        # Test avec utilisateur secrétariat (autorisé)
        self.client.login(username='secretariat_test', password='testpass123')
        response = self.client.get(reverse('events:create'))
        self.assertEqual(response.status_code, 200)
    
    def test_event_create_with_calendar_params(self):
        """Test la création d'événement avec paramètres du calendrier."""
        self.client.login(username='admin_test', password='testpass123')
        
        # Test avec date pré-remplie
        response = self.client.get(reverse('events:create') + '?date=2024-12-25')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2024-12-25')
        
        # Test avec titre pré-rempli
        response = self.client.get(reverse('events:create') + '?title=Nouvel%20Événement')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nouvel Événement')
    
    def test_event_update_view_permissions(self):
        """Test les permissions pour la modification d'événement."""
        # Test avec organisateur (autorisé)
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(reverse('events:update', kwargs={'pk': self.event.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Test avec utilisateur non-organisateur (pas autorisé sauf admin)
        self.client.login(username='secretariat_test', password='testpass123')
        response = self.client.get(reverse('events:update', kwargs={'pk': self.event.pk}))
        self.assertEqual(response.status_code, 302)  # Redirection (pas organisateur)
    
    def test_event_cancel_functionality(self):
        """Test l'annulation d'événement."""
        self.client.login(username='admin_test', password='testpass123')
        
        # Vérifier que l'événement n'est pas annulé initialement
        self.assertFalse(self.event.is_cancelled)
        
        # Tester l'affichage du formulaire d'annulation
        response = self.client.get(reverse('events:cancel', kwargs={'pk': self.event.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmation d\'annulation')
        
        # Tester l'annulation effective
        response = self.client.post(reverse('events:cancel', kwargs={'pk': self.event.pk}), {
            'reason': 'Test cancellation',
            'notify_participants': False
        })
        self.assertEqual(response.status_code, 302)  # Redirection après succès
        
        # Vérifier que l'événement est maintenant annulé
        self.event.refresh_from_db()
        self.assertTrue(self.event.is_cancelled)
    
    def test_event_duplicate_functionality(self):
        """Test la duplication d'événement."""
        self.client.login(username='admin_test', password='testpass123')
        
        # Tester l'affichage du formulaire de duplication
        response = self.client.get(reverse('events:duplicate', kwargs={'pk': self.event.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dupliquer un événement')
        
        # Compter les événements avant duplication
        initial_count = Event.objects.count()
        
        # Tester la duplication effective avec une date future
        from datetime import datetime, timedelta
        future_date = (datetime.now() + timedelta(days=30)).date()
        
        response = self.client.post(reverse('events:duplicate', kwargs={'pk': self.event.pk}), {
            'new_start_date': future_date.strftime('%Y-%m-%d'),
            'new_start_time': '15:00',
            'duplicate_title_suffix': ' (Copie Test)'
        })
        
        # Debug si la redirection n'a pas lieu
        if response.status_code != 302:
            print("Response status:", response.status_code)
            print("Response content:", response.content.decode()[:500])
        
        self.assertEqual(response.status_code, 302)  # Redirection après succès
        
        # Vérifier qu'un nouvel événement a été créé
        self.assertEqual(Event.objects.count(), initial_count + 1)
        
        # Vérifier les propriétés du nouvel événement
        new_event = Event.objects.exclude(pk=self.event.pk).first()
        self.assertIn('Test Event', new_event.title)
        self.assertIn('Copie Test', new_event.title)
        self.assertEqual(new_event.start_date, future_date)
        self.assertFalse(new_event.is_cancelled)
    
    def test_event_list_advanced_view(self):
        """Test la vue de liste avancée avec filtres."""
        self.client.login(username='admin_test', password='testpass123')
        
        response = self.client.get(reverse('events:list_advanced'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Filtres et recherche')
        
        # Test avec filtres
        response = self.client.get(reverse('events:list_advanced') + '?search=Test')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.title)
    
    def test_events_json_api(self):
        """Test l'API JSON pour FullCalendar."""
        self.client.login(username='admin_test', password='testpass123')
        
        response = self.client.get(reverse('events:events_json'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Vérifier que l'événement est dans la réponse
        import json
        data = json.loads(response.content)
        self.assertTrue(any(event['title'] == 'Test Event' for event in data))


class EventFormsTestCase(TestCase):
    """Tests pour les formulaires d'événements."""
    
    def setUp(self):
        """Configuration des tests."""
        self.category = EventCategory.objects.create(
            name='Test Category',
            color='#ff0000'
        )
    
    def test_event_form_validation(self):
        """Test la validation du formulaire d'événement."""
        # Test avec données valides
        form_data = {
            'title': 'Test Event',
            'start_date': date.today(),
            'category': self.category.pk,
            'visibility': 'public',
            'notification_scope': 'none',
            'notify_before': 1,
            'recurrence': 'none'  # Ajout du champ requis
        }
        form = EventForm(data=form_data)
        if not form.is_valid():
            print("Form errors:", form.errors)  # Debug
        self.assertTrue(form.is_valid())
        
        # Test avec date de fin antérieure à la date de début
        form_data['end_date'] = date(2020, 1, 1)  # Date dans le passé
        form = EventForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('La date de fin ne peut pas être antérieure', str(form.errors))
    
    def test_event_cancel_form(self):
        """Test le formulaire d'annulation."""
        form_data = {
            'reason': 'Test reason',
            'notify_participants': True
        }
        form = EventCancelForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_event_duplicate_form(self):
        """Test le formulaire de duplication."""
        from datetime import datetime, timedelta
        future_date = (datetime.now() + timedelta(days=30)).date()
        
        form_data = {
            'new_start_date': future_date,
            'duplicate_title_suffix': ' (Copie)'
        }
        form = EventDuplicateForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test avec date dans le passé
        form_data['new_start_date'] = date(2020, 1, 1)
        form = EventDuplicateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('La nouvelle date ne peut pas être dans le passé', str(form.errors))