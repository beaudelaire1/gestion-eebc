from decimal import Decimal

from django.utils import timezone

from apps.finance.models import OnlineDonation
from apps.finance.pdf_service import _build_donation_receipt_context, _render_donation_receipt_template


def test_online_donation_receipt_context_uses_system_code_for_automatic_receipts():
    donation = OnlineDonation(
        stripe_session_id='cs_test_operator_code',
        amount=Decimal('42.00'),
        donation_type=OnlineDonation.DonationType.DON,
        donor_email='donateur@example.com',
        donor_name='Donateur Exemple',
        status=OnlineDonation.Status.COMPLETED,
        created_at=timezone.now(),
    )

    context = _build_donation_receipt_context(donation, 'DON-202601-00042')
    html = _render_donation_receipt_template('donation_receipt.html.j2', context)

    assert context['operator_code'] == 'SYS-000000'
    assert 'Code utilisateur SYS-000000' in html