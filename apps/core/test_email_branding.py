"""Regression tests for the shared EEBC email identity."""

from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import get_template, render_to_string

pytestmark = pytest.mark.django_db


def _email_template_paths():
    template_root = Path(settings.BASE_DIR) / "templates"
    return sorted(
        path
        for path in template_root.rglob("*.html")
        if {"email", "emails"}.intersection(path.relative_to(template_root).parts)
    )


def test_all_email_templates_compile():
    template_root = Path(settings.BASE_DIR) / "templates"

    for path in _email_template_paths():
        get_template(path.relative_to(template_root).as_posix())


def test_all_email_templates_share_the_canonical_envelope():
    for path in _email_template_paths():
        if path.as_posix().endswith("templates/emails/base_email.html"):
            continue

        source = path.read_text(encoding="utf-8")
        assert "{% extends" in source, f"{path} bypasses the shared EEBC envelope"


@pytest.mark.parametrize(
    ("template_name", "context", "expected_heading"),
    [
        (
            "emails/donation_receipt.html",
            {
                "donor_name": "Marie Exemple",
                "amount": "125,00",
                "donation_type_label": "offrande spéciale",
                "reference": "DON-2026-0901",
                "donation_date": "01/09/2026",
            },
            "Merci pour votre générosité",
        ),
        (
            "communication/email/test.html",
            {"recipient_name": "Marie", "test_message": "Configuration opérationnelle."},
            "Test de configuration",
        ),
    ],
)
def test_representative_emails_render_with_branding(template_name, context, expected_heading):
    html = render_to_string(template_name, context)

    assert html.count("<html") == 1
    assert "eebc-logo.png" in html
    assert "Église Évangélique Baptiste de Cabassou" in html
    assert "La Bible, notre seule source d'autorité" in html
    assert expected_heading in html


def test_email_logo_supports_inline_cid_attachment():
    html = render_to_string(
        "emails/donation_receipt.html",
        {
            "EMAIL_LOGO_CID": "logo-eebc",
            "donor_name": "Marie Exemple",
            "amount": "50,00",
            "donation_type_label": "don",
            "reference": "DON-001",
            "donation_date": "01/09/2026",
        },
    )

    assert 'src="cid:logo-eebc"' in html
