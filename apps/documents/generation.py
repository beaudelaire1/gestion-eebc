"""Service de rendu PDF des documents générés via WeasyPrint."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from .richtext import sanitize_generated_document_html


BASE_THEME = {
    'institution_name': "Église Évangélique Baptiste de Cabassou",
    'institution_motto': "« La Bible, notre seule source d'autorité »",
    'document_city': getattr(settings, 'DOCUMENT_CITY', 'Cayenne'),
}


KIND_THEMES = {
    'courrier': {
        'accent': '#2d6cdf',
        'accent_dark': '#153a7a',
        'accent_soft': '#edf4ff',
        'accent_border': '#c6d8fb',
        'hero_overline': '',
        'classification': 'Courrier',
        'hero_title': 'Courrier',
        'hero_subtitle': '',
        'footer_label': 'Courrier',
        'recipient_label': 'Destinataire',
    },
    'compte_rendu': {
        'accent': '#13857d',
        'accent_dark': '#0c5954',
        'accent_soft': '#eaf9f7',
        'accent_border': '#bfe8e2',
        'hero_overline': '',
        'classification': 'Compte rendu',
        'hero_title': 'Compte rendu',
        'hero_subtitle': '',
        'footer_label': 'Compte rendu',
        'recipient_label': 'Diffusion',
    },
    'convocation': {
        'accent': '#d94b71',
        'accent_dark': '#7d1e3a',
        'accent_soft': '#fff0f5',
        'accent_border': '#f3bfd0',
        'hero_overline': '',
        'classification': 'Convocation',
        'hero_title': 'Convocation',
        'hero_subtitle': '',
        'footer_label': 'Convocation',
        'recipient_label': 'Personne convoquée',
    },
    'attestation': {
        'accent': '#1fa66d',
        'accent_dark': '#0f5a3d',
        'accent_soft': '#ecfbf4',
        'accent_border': '#bee9d5',
        'hero_overline': '',
        'classification': 'Attestation',
        'hero_title': 'Attestation',
        'hero_subtitle': '',
        'footer_label': 'Attestation',
        'recipient_label': 'Bénéficiaire',
    },
    'note_service': {
        'accent': '#5867e8',
        'accent_dark': '#29358d',
        'accent_soft': '#eef1ff',
        'accent_border': '#cad1ff',
        'hero_overline': '',
        'classification': 'Note de service',
        'hero_title': 'Note de service',
        'hero_subtitle': '',
        'footer_label': 'Note de service',
        'recipient_label': 'Diffusion interne',
    },
    'rapport': {
        'accent': '#d29a1f',
        'accent_dark': '#7a5208',
        'accent_soft': '#fff8e8',
        'accent_border': '#f0d79b',
        'hero_overline': '',
        'classification': 'Rapport',
        'hero_title': 'Rapport',
        'hero_subtitle': '',
        'footer_label': 'Rapport',
        'recipient_label': 'Diffusion',
    },
    'autre': {
        'accent': '#4f6b8a',
        'accent_dark': '#1d3047',
        'accent_soft': '#f1f5f9',
        'accent_border': '#d3dde7',
        'hero_overline': '',
        'classification': 'Document',
        'hero_title': 'Document',
        'hero_subtitle': '',
        'footer_label': 'Document',
        'recipient_label': 'Destinataire',
    },
}


def get_generated_document_theme(doc) -> dict:
    """Construit la charte graphique premium selon le type de document."""
    theme = {
        **BASE_THEME,
        **KIND_THEMES.get(getattr(doc, 'kind', ''), KIND_THEMES['autre']),
    }
    theme['kind_display'] = doc.get_kind_display()
    theme['subject_label'] = 'Objet'
    return theme


def build_generated_document_context(doc, *, logo_path='', generated_on=None) -> dict:
    """Contexte partagé entre aperçu HTML et rendu PDF."""
    return {
        'doc': doc,
        'body_html_rendered': sanitize_generated_document_html(getattr(doc, 'body_html', '')),
        'logo_path': logo_path,
        'generated_on': generated_on or timezone.now(),
        'theme': get_generated_document_theme(doc),
    }


def render_generated_document_pdf(doc) -> bytes:
    """Rend un GeneratedDocument en PDF (bytes) avec papeterie premium."""
    from weasyprint import HTML  # import local : weasyprint est lent à charger

    logo_path = Path(settings.BASE_DIR) / 'static' / 'images' / 'eebc-logo.png'
    logo_uri = logo_path.as_uri() if logo_path.exists() else ''

    html = render_to_string(
        'documents/generated/pdf_template.html',
        build_generated_document_context(doc, logo_path=logo_uri),
    )

    buf = BytesIO()
    HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf(target=buf)
    return buf.getvalue()
