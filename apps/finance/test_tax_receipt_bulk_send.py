"""Régression : l'envoi groupé des reçus fiscaux ne doit pas bloquer la requête.

La vue rendait un PDF WeasyPrint et ouvrait une connexion SMTP par reçu, en
synchrone. Au-delà de quelques dizaines de destinataires, le worker gunicorn
dépassait son délai et était tué — ce que le navigateur reçoit en 502.
"""

from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.finance.models import TaxReceipt
from apps.members.models import Member

pytestmark = pytest.mark.django_db


def _finance_user():
    return User.objects.create_superuser(
        username='finance-bulk',
        email='finance-bulk@example.test',
        password='SecurePass!2026',
        role='admin,finance',
    )


def _receipt(**kwargs):
    defaults = {
        'fiscal_year': 2026,
        'status': 'issued',
        'total_amount': 120,
    }
    defaults.update(kwargs)
    return TaxReceipt.objects.create(**defaults)


def test_bulk_send_queues_one_task_per_receipt_instead_of_blocking(client):
    user = _finance_user()
    client.force_login(user)

    _receipt(receipt_number='R-2026-001', donor_name='Alice Martin',
             donor_email='alice@example.test')
    _receipt(receipt_number='R-2026-002', donor_name='Bruno Ocema',
             donor_email='bruno@example.test')

    with patch('apps.finance.tasks.send_tax_receipt_email_task.delay') as queued:
        response = client.post(
            reverse('finance:tax_receipt_bulk_send'),
            {'fiscal_year': '2026'},
        )

    assert response.status_code == 302
    # Une tâche par reçu : un échec sur l'un n'emporte pas les autres.
    assert queued.call_count == 2


def test_bulk_send_skips_receipts_without_any_email(client):
    user = _finance_user()
    client.force_login(user)

    _receipt(receipt_number='R-2026-010', donor_name='Sans Contact', donor_email='')
    member = Member.objects.create(first_name='Avec', last_name='Membre',
                                   email='membre@example.test')
    _receipt(receipt_number='R-2026-011', donor_name='Avec Membre',
             donor_email='', member=member)

    with patch('apps.finance.tasks.send_tax_receipt_email_task.delay') as queued:
        client.post(reverse('finance:tax_receipt_bulk_send'), {'fiscal_year': '2026'})

    # L'adresse peut venir du reçu ou du membre lié ; le filtre se fait en SQL
    # et ne doit retenir que le second.
    assert queued.call_count == 1


def test_bulk_send_does_not_render_pdfs_in_the_request(client):
    """Le rendu PDF est ce qui faisait exploser le délai : il part au worker."""
    user = _finance_user()
    client.force_login(user)

    for i in range(5):
        _receipt(receipt_number=f'R-2026-1{i:02d}', donor_name=f'Donateur {i}',
                 donor_email=f'don{i}@example.test')

    with patch('apps.finance.tasks.send_tax_receipt_email_task.delay'), \
            patch('apps.finance.pdf_service.generate_tax_receipt_pdf') as pdf:
        client.post(reverse('finance:tax_receipt_bulk_send'), {'fiscal_year': '2026'})

    assert pdf.call_count == 0
