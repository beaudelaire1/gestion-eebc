"""
Tests pour le module Finance.

Couvre : FinancialTransaction, TaxReceipt, soft-delete, Budget.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone

from apps.finance.models import (
    FinancialTransaction,
    FinanceCategory,
    TaxReceipt,
    Budget,
    BudgetCategory,
    BudgetItem,
    BudgetForecast,
    ForecastLine,
)
from test_factories import (
    SiteFactory,
    UserFactory,
    MemberFactory,
    FinancialTransactionFactory,
    FinanceCategoryFactory,
)


# =============================================================================
# FinancialTransaction
# =============================================================================

class TestFinancialTransaction:
    """Tests pour le modèle FinancialTransaction."""

    def test_auto_reference_on_save(self, db):
        """La référence est auto-générée si absente."""
        tx = FinancialTransactionFactory()
        assert tx.reference
        assert tx.reference.startswith('TRX-')

    def test_reference_not_overwritten(self, db):
        """Une référence existante n'est pas écrasée."""
        tx = FinancialTransactionFactory(reference='MY-REF-001')
        assert tx.reference == 'MY-REF-001'

    def test_is_income_for_don(self, db):
        """Un don est une entrée d'argent."""
        tx = FinancialTransactionFactory(transaction_type='don')
        assert tx.is_income is True

    def test_is_income_for_dime(self, db):
        """Une dîme est une entrée d'argent."""
        tx = FinancialTransactionFactory(transaction_type='dime')
        assert tx.is_income is True

    def test_is_income_for_depense(self, db):
        """Une dépense n'est pas une entrée d'argent."""
        tx = FinancialTransactionFactory(transaction_type='depense')
        assert tx.is_income is False

    def test_signed_amount_income(self, db):
        """Le montant signé est positif pour un don."""
        tx = FinancialTransactionFactory(transaction_type='don', amount=Decimal('100.00'))
        assert tx.signed_amount == Decimal('100.00')

    def test_signed_amount_expense(self, db):
        """Le montant signé est négatif pour une dépense."""
        tx = FinancialTransactionFactory(transaction_type='depense', amount=Decimal('50.00'))
        assert tx.signed_amount == Decimal('-50.00')

    def test_soft_delete(self, db):
        """soft_delete marque la transaction comme supprimée."""
        user = UserFactory()
        tx = FinancialTransactionFactory()
        tx.soft_delete(user)

        tx.refresh_from_db()
        assert tx.is_deleted is True
        assert tx.deleted_by == user
        assert tx.deleted_at is not None

    def test_soft_delete_hides_from_default_manager(self, db):
        """Les transactions soft-deleted sont exclues du manager par défaut."""
        user = UserFactory()
        tx = FinancialTransactionFactory()
        pk = tx.pk
        tx.soft_delete(user)

        assert FinancialTransaction.objects.filter(pk=pk).exists() is False
        assert FinancialTransaction.all_objects.filter(pk=pk).exists() is True

    def test_restore(self, db):
        """restore() restaure une transaction supprimée."""
        user = UserFactory()
        tx = FinancialTransactionFactory()
        tx.soft_delete(user)
        tx.restore()

        tx.refresh_from_db()
        assert tx.is_deleted is False
        assert tx.deleted_by is None

    def test_hard_delete_not_allowed(self, db):
        """delete() lève NotImplementedError."""
        tx = FinancialTransactionFactory()
        with pytest.raises(NotImplementedError):
            tx.delete()

    def test_hard_delete(self, db):
        """hard_delete() supprime réellement."""
        tx = FinancialTransactionFactory()
        pk = tx.pk
        tx.hard_delete()
        assert FinancialTransaction.all_objects.filter(pk=pk).exists() is False

    def test_str_representation(self, db):
        """__str__ contient la référence et le montant."""
        tx = FinancialTransactionFactory(amount=Decimal('250.00'))
        s = str(tx)
        assert tx.reference in s
        assert '250' in s


# =============================================================================
# TaxReceipt
# =============================================================================

class TestTaxReceipt:
    """Tests pour le modèle TaxReceipt."""

    def test_receipt_number_auto_generated(self, db):
        """Le numéro de reçu est généré automatiquement."""
        member = MemberFactory()
        receipt = TaxReceipt.objects.create(
            donor_name=f"{member.first_name} {member.last_name}",
            donor_email=member.email,
            donor_address="1 rue Test, 97300 Cayenne",
            fiscal_year=2025,
            total_amount=Decimal('500.00'),
            member=member,
        )
        assert receipt.receipt_number
        assert 'RF-' in receipt.receipt_number

    def test_status_default_draft(self, db):
        """Le statut par défaut est DRAFT."""
        receipt = TaxReceipt.objects.create(
            donor_name="Test Donor",
            donor_email="donor@test.com",
            donor_address="1 rue Test",
            fiscal_year=2025,
            total_amount=Decimal('100.00'),
        )
        assert receipt.status == TaxReceipt.Status.DRAFT


# =============================================================================
# Budget
# =============================================================================

class TestBudget:
    """Tests pour le système de budget."""

    def test_budget_creation(self, db):
        """Un budget peut être créé avec des items."""
        user = UserFactory(role='admin')
        cat = BudgetCategory.objects.create(name="Événements", color="#FF0000")

        budget = Budget.objects.create(
            name="Budget 2025",
            year=2025,
            total_requested=Decimal('5000.00'),
            total_approved=Decimal('4000.00'),
            status=Budget.Status.APPROVED,
            created_by=user,
        )

        item = BudgetItem.objects.create(
            budget=budget,
            category=cat,
            description="Matériel sono",
            requested_amount=Decimal('2000.00'),
            approved_amount=Decimal('1500.00'),
        )

        assert budget.status == Budget.Status.APPROVED
        assert item.requested_amount == Decimal('2000.00')
        assert item.approved_amount == Decimal('1500.00')


@pytest.mark.django_db
class TestBudgetForecastEdit:
    """Tests de l'edition des previsionnels budgetaires."""

    def test_forecast_edit_form_exposes_editable_year(self, authenticated_client, admin_user):
        forecast = BudgetForecast.objects.create(
            name="Budget previsionnel 2025",
            year=2025,
            scenario=BudgetForecast.Scenario.REALISTIC,
            created_by=admin_user,
        )

        response = authenticated_client.get(reverse('finance:forecast_edit', args=[forecast.pk]))

        assert response.status_code == 200
        content = response.content.decode()
        assert 'name="year"' in content
        assert 'id="year"' in content
        assert 'type="number"' in content

    def test_forecast_edit_updates_year(self, authenticated_client, admin_user):
        category = FinanceCategoryFactory()
        forecast = BudgetForecast.objects.create(
            name="Budget previsionnel 2025",
            year=2025,
            scenario=BudgetForecast.Scenario.REALISTIC,
            description="Version initiale",
            created_by=admin_user,
        )
        ForecastLine.objects.create(
            forecast=forecast,
            label="Dime",
            line_type=ForecastLine.LineType.INCOME,
            category=category,
            jan=Decimal('10.00'),
        )

        response = authenticated_client.post(
            reverse('finance:forecast_edit', args=[forecast.pk]),
            {
                'name': 'Budget previsionnel 2026',
                'year': '2026',
                'description': 'Version revue',
                'line_0_label': 'Dime',
                'line_0_type': ForecastLine.LineType.INCOME,
                'line_0_category': str(category.pk),
                'line_0_jan': '10.00',
            },
            follow=True,
        )

        forecast.refresh_from_db()

        assert response.status_code == 200
        assert forecast.year == 2026
        assert forecast.name == 'Budget previsionnel 2026'
        assert forecast.description == 'Version revue'
