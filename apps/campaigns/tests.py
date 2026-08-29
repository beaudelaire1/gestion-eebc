"""
Tests pour l'app campaigns — modèles, logique métier.
"""
import pytest
from decimal import Decimal
from django.utils import timezone

from apps.accounts.models import User
from apps.campaigns.models import Campaign, Donation


@pytest.fixture
def site(db):
    from apps.core.models import Site
    return Site.objects.first() or Site.objects.create(name='Cayenne', code='CAY')


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='campuser', email='camp@example.com', password='Pass123!'
    )


@pytest.fixture
def campaign(db, site, user):
    return Campaign.objects.create(
        name='Construction Temple',
        description='Campagne pour la construction',
        site=site,
        goal_amount=Decimal('50000.00'),
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timezone.timedelta(days=90),
        responsible=user,
        is_active=True,
    )


@pytest.mark.django_db
class TestCampaign:

    def test_create_campaign(self, campaign):
        assert campaign.pk is not None
        assert 'Construction Temple' in str(campaign)

    def test_progress_percentage_zero(self, campaign):
        assert campaign.progress_percentage == 0

    def test_remaining_amount(self, campaign):
        assert campaign.remaining_amount == Decimal('50000.00')

    def test_progress_with_donation(self, campaign):
        Donation.objects.create(
            campaign=campaign,
            donor_name='Jean',
            amount=Decimal('10000.00'),
            donation_date=timezone.now().date(),
        )
        campaign.refresh_from_db()
        assert campaign.collected_amount == Decimal('10000.00')
        assert campaign.progress_percentage == 20


@pytest.mark.django_db
class TestDonation:

    def test_create_donation(self, campaign):
        don = Donation.objects.create(
            campaign=campaign,
            donor_name='Marie Dupont',
            amount=Decimal('500.00'),
            donation_date=timezone.now().date(),
        )
        assert don.pk is not None
        assert str(don)

    def test_anonymous_donation(self, campaign):
        don = Donation.objects.create(
            campaign=campaign,
            donor_name='',
            is_anonymous=True,
            amount=Decimal('100.00'),
            donation_date=timezone.now().date(),
        )
        assert don.is_anonymous is True

    def test_donation_updates_campaign_total(self, campaign):
        Donation.objects.create(
            campaign=campaign,
            donor_name='Don 1',
            amount=Decimal('1000.00'),
            donation_date=timezone.now().date(),
        )
        Donation.objects.create(
            campaign=campaign,
            donor_name='Don 2',
            amount=Decimal('2000.00'),
            donation_date=timezone.now().date(),
        )
        campaign.refresh_from_db()
        assert campaign.collected_amount == Decimal('3000.00')

    def test_cancelled_donation(self, campaign):
        don = Donation.objects.create(
            campaign=campaign,
            donor_name='Cancel',
            amount=Decimal('500.00'),
            donation_date=timezone.now().date(),
            is_cancelled=True,
        )
        assert don.is_cancelled is True
