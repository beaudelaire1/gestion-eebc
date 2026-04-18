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
    'paper_style': 'standard-brief',
    'display_font': 'Cambria, Times New Roman, serif',
    'body_font': 'Aptos, Segoe UI, Arial, sans-serif',
    'meta_font': 'Segoe UI, Arial, sans-serif',
    'title_label': 'Intitulé du document',
    'hero_subtitle': '',
    'watermark_text': 'EEBC',
}


KIND_THEMES = {
    'courrier': {
        'accent': '#2d6cdf',
        'accent_dark': '#153a7a',
        'accent_soft': '#edf4ff',
        'accent_border': '#c6d8fb',
        'paper_style': 'classic-letter',
        'display_font': 'Cambria, Times New Roman, serif',
        'body_font': 'Aptos, Segoe UI, Arial, sans-serif',
        'meta_font': 'Segoe UI, Arial, sans-serif',
        'hero_overline': 'Correspondance officielle',
        'classification': 'Courrier',
        'hero_title': 'Courrier',
        'hero_subtitle': '',
        'footer_label': 'Courrier',
        'recipient_label': 'Destinataire',
        'title_label': 'Objet du courrier',
        'watermark_text': 'EEBC',
    },
    'compte_rendu': {
        'accent': '#13857d',
        'accent_dark': '#0c5954',
        'accent_soft': '#eaf9f7',
        'accent_border': '#bfe8e2',
        'paper_style': 'meeting-minutes',
        'display_font': 'Georgia, Times New Roman, serif',
        'body_font': 'Calibri, Segoe UI, Arial, sans-serif',
        'meta_font': 'Segoe UI, Arial, sans-serif',
        'hero_overline': 'Mémoire de séance',
        'classification': 'Compte rendu',
        'hero_title': 'Compte rendu',
        'hero_subtitle': 'Décisions actées, points examinés et actions de suivi.',
        'footer_label': 'Compte rendu',
        'recipient_label': 'Diffusion',
        'subject_label': 'Synthèse',
        'title_label': 'Séance concernée',
        'watermark_text': 'CR',
    },
    'convocation': {
        'accent': '#d94b71',
        'accent_dark': '#7d1e3a',
        'accent_soft': '#fff0f5',
        'accent_border': '#f3bfd0',
        'paper_style': 'ceremonial-call',
        'display_font': 'Palatino Linotype, Book Antiqua, Georgia, serif',
        'body_font': 'Aptos, Segoe UI, Arial, sans-serif',
        'meta_font': 'Segoe UI, Arial, sans-serif',
        'hero_overline': 'Avis de réunion',
        'classification': 'Convocation',
        'hero_title': 'Convocation',
        'hero_subtitle': 'Présence requise pour la séance mentionnée au présent document.',
        'footer_label': 'Convocation',
        'recipient_label': 'Personne convoquée',
        'title_label': 'Séance convoquée',
        'watermark_text': 'CONVOC',
    },
    'attestation': {
        'accent': '#1fa66d',
        'accent_dark': '#0f5a3d',
        'accent_soft': '#ecfbf4',
        'accent_border': '#bee9d5',
        'paper_style': 'certificate',
        'display_font': 'Palatino Linotype, Book Antiqua, Georgia, serif',
        'body_font': 'Calibri, Segoe UI, Arial, sans-serif',
        'meta_font': 'Segoe UI, Arial, sans-serif',
        'hero_overline': 'Document certifié',
        'classification': 'Attestation',
        'hero_title': 'Attestation',
        'hero_subtitle': 'Acte officiel établi pour faire foi de la situation attestée.',
        'footer_label': 'Attestation',
        'recipient_label': 'Bénéficiaire',
        'subject_label': 'Référence',
        'title_label': 'Nature de l\'attestation',
        'watermark_text': 'ATTESTE',
    },
    'note_service': {
        'accent': '#5867e8',
        'accent_dark': '#29358d',
        'accent_soft': '#eef1ff',
        'accent_border': '#cad1ff',
        'paper_style': 'internal-memo',
        'display_font': 'Segoe UI, Arial, sans-serif',
        'body_font': 'Segoe UI, Arial, sans-serif',
        'meta_font': 'Segoe UI, Arial, sans-serif',
        'hero_overline': 'Circulation interne',
        'classification': 'Note de service',
        'hero_title': 'Note de service',
        'hero_subtitle': 'Instruction courte, exploitable et directement diffusée aux équipes.',
        'footer_label': 'Note de service',
        'recipient_label': 'Diffusion interne',
        'subject_label': 'Note',
        'title_label': 'Message de service',
        'watermark_text': 'NOTE',
    },
    'rapport': {
        'accent': '#d29a1f',
        'accent_dark': '#7a5208',
        'accent_soft': '#fff8e8',
        'accent_border': '#f0d79b',
        'paper_style': 'editorial-report',
        'display_font': 'Trebuchet MS, Segoe UI, Arial, sans-serif',
        'body_font': 'Calibri, Segoe UI, Arial, sans-serif',
        'meta_font': 'Segoe UI, Arial, sans-serif',
        'hero_overline': 'Analyse et synthèse',
        'classification': 'Rapport',
        'hero_title': 'Rapport',
        'hero_subtitle': 'Vision structurée pour l\'archivage, le suivi et la prise de décision.',
        'footer_label': 'Rapport',
        'recipient_label': 'Diffusion',
        'subject_label': 'Sujet',
        'title_label': 'Titre du rapport',
        'watermark_text': 'RAPPORT',
    },
    'autre': {
        'accent': '#4f6b8a',
        'accent_dark': '#1d3047',
        'accent_soft': '#f1f5f9',
        'accent_border': '#d3dde7',
        'paper_style': 'standard-brief',
        'display_font': 'Cambria, Times New Roman, serif',
        'body_font': 'Aptos, Segoe UI, Arial, sans-serif',
        'meta_font': 'Segoe UI, Arial, sans-serif',
        'hero_overline': 'Document administratif',
        'classification': 'Document',
        'hero_title': 'Document',
        'hero_subtitle': 'Support rédigé pour diffusion, conservation et suivi administratif.',
        'footer_label': 'Document',
        'recipient_label': 'Destinataire',
        'title_label': 'Intitulé du document',
        'watermark_text': 'EEBC',
    },
}


def get_generated_document_theme(doc) -> dict:
    """Construit la charte graphique premium selon le type de document."""
    theme = {
        **BASE_THEME,
        **KIND_THEMES.get(getattr(doc, 'kind', ''), KIND_THEMES['autre']),
    }
    theme['kind_display'] = doc.get_kind_display()
    theme.setdefault('subject_label', 'Objet')
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
