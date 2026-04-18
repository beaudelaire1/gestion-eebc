"""Service de rendu PDF des documents générés via WeasyPrint."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone


def render_generated_document_pdf(doc) -> bytes:
    """Rend un GeneratedDocument en PDF (bytes) avec entête + logo."""
    from weasyprint import HTML  # import local : weasyprint est lent à charger

    logo_path = Path(settings.BASE_DIR) / 'static' / 'images' / 'eebc-logo.png'
    logo_uri = logo_path.as_uri() if logo_path.exists() else ''

    html = render_to_string('documents/generated/pdf_template.html', {
        'doc': doc,
        'logo_path': logo_uri,
        'generated_on': timezone.now(),
    })

    buf = BytesIO()
    HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf(target=buf)
    return buf.getvalue()
