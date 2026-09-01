"""Tout document remis à un tiers doit permettre de joindre l'organisme.

L'adresse et l'email étaient soit absents, soit écrits en dur dans le template :
un déménagement ou un changement d'adresse email aurait laissé des documents
mentir sans que personne ne s'en aperçoive.
"""

import pytest
from django.template.loader import render_to_string

from apps.core.church import CHURCH_INFO, church_contact_line


EXTERNAL_DOCUMENTS = [
    'finance/report_pdf.html',
    'finance/member_donation_detail_pdf.html',
    'members/pdf/registration_form.html',
    'bibleclub/pdf/registration_form.html',
    'young/pdf/registration_form.html',
]


@pytest.mark.parametrize('template_name', EXTERNAL_DOCUMENTS)
def test_document_carries_the_church_identity(template_name):
    html = render_to_string(template_name, {})

    assert CHURCH_INFO['address'] in html, template_name
    assert CHURCH_INFO['email'] in html, template_name


def test_contact_line_omits_the_separator_when_only_one_value_is_set(monkeypatch):
    monkeypatch.setitem(CHURCH_INFO, 'phone', '')
    assert church_contact_line() == CHURCH_INFO['email']

    monkeypatch.setitem(CHURCH_INFO, 'phone', '+594 594 00 00 00')
    assert church_contact_line() == f"+594 594 00 00 00 — {CHURCH_INFO['email']}"
