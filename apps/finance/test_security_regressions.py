from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.finance.models import OnlineDonation, TaxReceipt

pytestmark = [pytest.mark.django_db, pytest.mark.security]


def _finance_user():
    return User.objects.create_user(
        username='finance-security',
        email='finance-security@example.test',
        password='SecurePass!2026',
        role='finance',
    )


def test_leaked_stripe_session_id_cannot_download_receipt(client):
    donation = OnlineDonation.objects.create(
        stripe_session_id='cs_test_leaked_capability',
        amount=Decimal('25.00'),
        donation_type=OnlineDonation.DonationType.DON,
        donor_email='donor-private@example.test',
        donor_name='Private Donor',
        status=OnlineDonation.Status.COMPLETED,
    )

    response = client.get(
        reverse('public:donation_receipt_pdf', kwargs={'session_id': donation.stripe_session_id})
    )

    assert response.status_code == 404


def test_leaked_stripe_session_id_does_not_expose_success_page_donor_data(client):
    donation = OnlineDonation.objects.create(
        stripe_session_id='cs_test_success_leak',
        amount=Decimal('40.00'),
        donation_type=OnlineDonation.DonationType.DON,
        donor_email='hidden-donor@example.test',
        donor_name='Hidden Donor',
        status=OnlineDonation.Status.COMPLETED,
    )

    response = client.get(
        reverse('public:donation_success'),
        {'session_id': donation.stripe_session_id},
    )

    assert response.status_code == 200
    body = response.content.decode('utf-8')
    assert 'hidden-donor@example.test' not in body
    assert '40.00' not in body


def test_tax_receipt_pdf_get_does_not_issue_receipt(client, monkeypatch):
    finance = _finance_user()
    receipt = TaxReceipt.objects.create(
        receipt_number='RF-2026-SEC1',
        fiscal_year=2026,
        donor_name='Audit Donor',
        donor_address='Cayenne',
        donor_email='audit-donor@example.test',
        total_amount=Decimal('100.00'),
        issued_by=finance,
        status=TaxReceipt.Status.DRAFT,
    )
    monkeypatch.setattr(
        'apps.finance.pdf_service.generate_tax_receipt_pdf',
        lambda _receipt: b'%PDF-1.4 security-test',
    )
    client.force_login(finance)

    response = client.get(reverse('finance:tax_receipt_pdf', kwargs={'pk': receipt.pk}))

    assert response.status_code == 200
    receipt.refresh_from_db()
    assert receipt.status == TaxReceipt.Status.DRAFT
    assert receipt.issue_date is None
