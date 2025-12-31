from django.test import TestCase
from datetime import date, timedelta
from decimal import Decimal

from .models import Campaign, Donation


class CampaignTests(TestCase):
    """Tests pour le modele Campaign."""
    
    def test_create_campaign(self):
        """Test creation d'une campagne."""
        campaign = Campaign.objects.create(
            name='Test Campaign',
            goal_amount=Decimal('1000.00'),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30)
        )
        self.assertEqual(campaign.progress_percentage, 0)
        self.assertEqual(campaign.remaining_amount, Decimal('1000.00'))
    
    def test_campaign_progress(self):
        """Test calcul de progression."""
        campaign = Campaign.objects.create(
            name='Test Campaign',
            goal_amount=Decimal('1000.00'),
            collected_amount=Decimal('500.00'),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30)
        )
        self.assertEqual(campaign.progress_percentage, 50)
        self.assertEqual(campaign.remaining_amount, Decimal('500.00'))
    
    def test_campaign_status_color(self):
        """Test couleur de statut."""
        # Campagne terminee avec succes
        campaign = Campaign.objects.create(
            name='Complete',
            goal_amount=Decimal('100.00'),
            collected_amount=Decimal('100.00'),
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() + timedelta(days=10)
        )
        self.assertEqual(campaign.status_color, 'success')
    
    def test_critical_campaign(self):
        """Test detection campagne critique."""
        campaign = Campaign.objects.create(
            name='Critical',
            goal_amount=Decimal('1000.00'),
            collected_amount=Decimal('100.00'),  # 10%
            start_date=date.today() - timedelta(days=20),
            end_date=date.today() + timedelta(days=7)  # 1 semaine
        )
        self.assertTrue(campaign.is_critical)


class DonationTests(TestCase):
    """Tests pour le modele Donation."""
    
    def setUp(self):
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            goal_amount=Decimal('1000.00'),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30)
        )
    
    def test_create_donation(self):
        """Test creation d'un don."""
        donation = Donation.objects.create(
            campaign=self.campaign,
            donor_name='Jean Genereux',
            amount=Decimal('100.00')
        )
        
        # Le montant collecte doit etre mis a jour
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.collected_amount, Decimal('100.00'))
    
    def test_anonymous_donation(self):
        """Test don anonyme."""
        donation = Donation.objects.create(
            campaign=self.campaign,
            is_anonymous=True,
            amount=Decimal('50.00')
        )
        self.assertIn('Anonyme', str(donation))

