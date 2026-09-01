"""Un document officiel doit permettre de joindre l'organisme.

Attestations, courriers et mémos n'affichaient que le nom de l'église et sa
devise : leur destinataire n'avait ni adresse, ni téléphone, ni email pour
répondre.
"""

import pytest
from django.template.loader import render_to_string

from apps.core.church import CHURCH_INFO, church_contact_line
from apps.documents.generation import build_generated_document_context

pytestmark = pytest.mark.django_db


class _Doc:
    kind = 'courrier'
    reference = 'EEBC-2026-001'
    body_html = '<p>Bonjour</p>'
    document_date = None
    recipient_name = ''
    recipient_address = ''
    subject = ''

    def get_kind_display(self):
        return 'Courrier'


def _render():
    context = build_generated_document_context(_Doc())
    return render_to_string('documents/generated/_document_markup.html', context)


def test_theme_exposes_the_shared_identity():
    context = build_generated_document_context(_Doc())

    assert context['theme']['institution_name'] == CHURCH_INFO['name']
    assert context['theme']['institution_address'] == CHURCH_INFO['address']


def test_generated_document_shows_address_and_contact():
    html = _render()

    assert CHURCH_INFO['address'] in html
    assert CHURCH_INFO['email'] in html


def test_contact_line_has_no_orphan_separator_without_phone(monkeypatch):
    monkeypatch.setitem(CHURCH_INFO, 'phone', '')

    assert church_contact_line() == CHURCH_INFO['email']
