"""Le reçu fiscal doit permettre de joindre l'organisme.

C'est le seul document que le donateur conserve et présente à l'administration.
Il ne portait que la dénomination et l'adresse postale : un donateur constatant
une erreur de montant ou d'adresse n'avait aucun moyen de réponse. Les reçus de
don, eux, affichaient déjà une ligne de contact.
"""

import importlib
from decimal import Decimal
from types import SimpleNamespace

from django.template.loader import render_to_string

from apps.finance import pdf_service


def _fake_receipt():
    return SimpleNamespace(total_amount=Decimal('120.00'))


def test_context_carries_contact_details():
    context = pdf_service.build_tax_receipt_context(_fake_receipt())

    assert context['church_email']
    assert 'church_phone' in context


def test_rendered_receipt_shows_how_to_reach_the_church():
    context = pdf_service.build_tax_receipt_context(_fake_receipt())
    context['church_phone'] = '+594 594 00 00 00'
    context['church_email'] = 'contact@example.test'

    html = render_to_string('finance/tax_receipt_pdf.html', context)

    assert 'contact@example.test' in html
    assert '+594 594 00 00 00' in html


def test_identity_survives_environment_variables_set_to_empty(monkeypatch):
    """Une variable définie mais vide ne doit pas effacer l'organisme."""
    for name in ('CHURCH_NAME', 'CHURCH_ADDRESS', 'CHURCH_EMAIL'):
        monkeypatch.setenv(name, '')

    reloaded = importlib.reload(pdf_service)
    try:
        assert reloaded.CHURCH_INFO['name']
        assert reloaded.CHURCH_INFO['address']
        assert reloaded.CHURCH_INFO['email']
    finally:
        monkeypatch.undo()
        importlib.reload(pdf_service)
