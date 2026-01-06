from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from decimal import Decimal
from datetime import date, timedelta
from .models import Campaign, Donation

User = get_user_model()


class CampaignCRUDTestCase(TestCase):
    """Tests pour les opérations CRUD des campagnes."""
    
    def setUp(self):
        self.client = Client()
        
        # Créer des utilisateurs avec différents rôles
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            role='admin'
        )
        
        self.finance_user = User.objects.create_user(
            username='finance',
            password='testpass123',
            role='finance'
        )
        
        self.membre_user = User.objects.create_user(
            username='membre',
            password='testpass123',
            role='membre'
        )
        
        # Créer une campagne de test
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            description='Une campagne de test',
            goal_amount=Decimal('1000.00'),
            collected_amount=Decimal('0.00'),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            responsible=self.admin_user
        )
    
    def test_campaign_list_view(self):
        """Test de la vue liste des campagnes."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('campaigns:list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Campaign')
        self.assertContains(response, 'Campagnes')
    
    def test_campaign_detail_view(self):
        """Test de la vue détail d'une campagne."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('campaigns:detail', kwargs={'pk': self.campaign.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.campaign.name)
        self.assertContains(response, '1000€')
    
    def test_campaign_create_view_admin(self):
        """Test de création de campagne par un admin."""
        self.client.login(username='admin', password='testpass123')
        
        # GET request
        response = self.client.get(reverse('campaigns:create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nouvelle campagne')
        
        # POST request
        data = {
            'name': 'Nouvelle Campagne',
            'description': 'Description de test',
            'goal_amount': '2000.00',
            'start_date': date.today().strftime('%Y-%m-%d'),
            'end_date': (date.today() + timedelta(days=60)).strftime('%Y-%m-%d'),
            'is_active': True
        }
        
        response = self.client.post(reverse('campaigns:create'), data)
        self.assertEqual(response.status_code, 302)  # Redirection après création
        
        # Vérifier que la campagne a été créée
        new_campaign = Campaign.objects.get(name='Nouvelle Campagne')
        self.assertEqual(new_campaign.goal_amount, Decimal('2000.00'))
    
    def test_campaign_create_view_finance(self):
        """Test de création de campagne par un utilisateur finance."""
        self.client.login(username='finance', password='testpass123')
        response = self.client.get(reverse('campaigns:create'))
        self.assertEqual(response.status_code, 200)
    
    def test_campaign_create_view_unauthorized(self):
        """Test de création de campagne par un utilisateur non autorisé."""
        self.client.login(username='membre', password='testpass123')
        response = self.client.get(reverse('campaigns:create'))
        self.assertEqual(response.status_code, 302)  # Redirection vers dashboard
    
    def test_campaign_update_view(self):
        """Test de modification d'une campagne."""
        self.client.login(username='admin', password='testpass123')
        
        # GET request
        response = self.client.get(reverse('campaigns:update', kwargs={'pk': self.campaign.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Modifier')
        
        # POST request
        data = {
            'name': 'Campagne Modifiée',
            'description': self.campaign.description,
            'goal_amount': '1500.00',
            'start_date': self.campaign.start_date.strftime('%Y-%m-%d'),
            'end_date': self.campaign.end_date.strftime('%Y-%m-%d'),
            'is_active': True
        }
        
        response = self.client.post(reverse('campaigns:update', kwargs={'pk': self.campaign.pk}), data)
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que la campagne a été modifiée
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.name, 'Campagne Modifiée')
        self.assertEqual(self.campaign.goal_amount, Decimal('1500.00'))
    
    def test_campaign_donate_view(self):
        """Test d'ajout de don à une campagne."""
        self.client.login(username='admin', password='testpass123')
        
        # GET request
        response = self.client.get(reverse('campaigns:donate', kwargs={'pk': self.campaign.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nouveau don')
        
        # POST request
        data = {
            'campaign': self.campaign.pk,
            'donor_name': 'Jean Dupont',
            'is_anonymous': False,
            'amount': '250.00',
            'notes': 'Don de test'
        }
        
        response = self.client.post(reverse('campaigns:donate', kwargs={'pk': self.campaign.pk}), data)
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que le don a été créé et que le montant collecté a été mis à jour
        donation = Donation.objects.get(donor_name='Jean Dupont')
        self.assertEqual(donation.amount, Decimal('250.00'))
        
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.collected_amount, Decimal('250.00'))
    
    def test_goal_reached_notification(self):
        """Test de la notification quand l'objectif est atteint."""
        self.client.login(username='admin', password='testpass123')
        
        # Ajouter un don qui atteint l'objectif
        data = {
            'campaign': self.campaign.pk,
            'donor_name': 'Gros Donateur',
            'is_anonymous': False,
            'amount': '1000.00',  # Atteint exactement l'objectif
            'notes': 'Don qui atteint l\'objectif'
        }
        
        response = self.client.post(reverse('campaigns:donate', kwargs={'pk': self.campaign.pk}), data)
        self.assertEqual(response.status_code, 302)
        
        # Vérifier les messages
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 2)  # Message de succès + message d'objectif atteint
        
        # Vérifier que l'un des messages contient "objectif" et "atteint"
        goal_message = None
        for message in messages:
            if 'objectif' in str(message) and 'atteint' in str(message):
                goal_message = message
                break
        
        self.assertIsNotNone(goal_message)
        self.assertIn('goal-reached', goal_message.tags)
    
    def test_campaign_progress_api(self):
        """Test de l'API de progression d'une campagne."""
        self.client.login(username='admin', password='testpass123')
        
        # Ajouter un don
        Donation.objects.create(
            campaign=self.campaign,
            donor_name='Test Donor',
            amount=Decimal('300.00')
        )
        
        response = self.client.get(reverse('campaigns:progress_api', kwargs={'pk': self.campaign.pk}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['collected_amount'], 300.0)
        self.assertEqual(data['goal_amount'], 1000.0)
        self.assertEqual(data['progress_percentage'], 30)
        self.assertEqual(data['remaining_amount'], 700.0)
        self.assertFalse(data['goal_reached'])
    
    def test_anonymous_donation(self):
        """Test de don anonyme."""
        self.client.login(username='admin', password='testpass123')
        
        data = {
            'campaign': self.campaign.pk,
            'donor_name': '',  # Nom vide
            'is_anonymous': True,
            'amount': '150.00',
            'notes': 'Don anonyme'
        }
        
        response = self.client.post(reverse('campaigns:donate', kwargs={'pk': self.campaign.pk}), data)
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que le don anonyme a été créé
        donation = Donation.objects.get(is_anonymous=True)
        self.assertEqual(donation.amount, Decimal('150.00'))
        self.assertEqual(donation.donor_name, '')
    
    def test_form_validation(self):
        """Test de validation des formulaires."""
        self.client.login(username='admin', password='testpass123')
        
        # Test avec dates invalides (fin avant début)
        data = {
            'name': 'Campagne Invalide',
            'goal_amount': '1000.00',
            'start_date': (date.today() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'end_date': date.today().strftime('%Y-%m-%d'),  # Fin avant début
            'is_active': True
        }
        
        response = self.client.post(reverse('campaigns:create'), data)
        self.assertEqual(response.status_code, 200)  # Reste sur la page avec erreurs
        self.assertContains(response, 'postérieure')  # Message d'erreur
        
        # Test avec montant négatif
        data = {
            'campaign': self.campaign.pk,
            'donor_name': 'Test',
            'is_anonymous': False,
            'amount': '-50.00',  # Montant négatif
        }
        
        response = self.client.post(reverse('campaigns:donate', kwargs={'pk': self.campaign.pk}), data)
        self.assertEqual(response.status_code, 200)  # Reste sur la page avec erreurs