"""
Service de génération PDF pour les reçus fiscaux et reçus de dons.

Utilise WeasyPrint pour générer des PDF conformes.
"""

import io
import os
import logging
import base64
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─── Informations de l'église (centralisées) ────────────────────────────────
CHURCH_INFO = {
    'name': os.environ.get('CHURCH_NAME', "Église Évangélique Baptiste de Cabassou"),
    'address': os.environ.get('CHURCH_ADDRESS', "11 lot Calimbé 2, rte de Cabassou, 97300 Cayenne"),
    'phone': os.environ.get('CHURCH_PHONE', ""),
    'email': os.environ.get('CHURCH_EMAIL', "contact@eglise-ebc.org"),
    'siret': os.environ.get('CHURCH_SIRET', ""),
    'rna': os.environ.get('CHURCH_RNA', ""),
}

DONATION_RECEIPT_TEMPLATE_DIR = Path(settings.BASE_DIR) / 'apps' / 'finance' / 'pdf_templates'
FRENCH_MONTHS = (
    'janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre',
)


def generate_tax_receipt_pdf(tax_receipt):
    """
    Génère le PDF d'un reçu fiscal.
    
    Args:
        tax_receipt: Instance de TaxReceipt
    
    Returns:
        bytes: Contenu du PDF
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        raise ImportError("WeasyPrint n'est pas installé. Installez-le avec: pip install weasyprint")
    
    # Charger le logo
    logo_base64 = _get_logo_base64()

    # Contexte pour le template
    context = {
        'receipt': tax_receipt,
        'logo_base64': logo_base64,
        'church_name': CHURCH_INFO['name'],
        'church_address': CHURCH_INFO['address'],
        'church_siret': CHURCH_INFO['siret'],
        'church_rna': CHURCH_INFO['rna'],
        'amount_words': _amount_to_words(tax_receipt.total_amount),
    }
    
    # Rendre le template HTML
    html_content = render_to_string('finance/tax_receipt_pdf.html', context)
    
    # CSS pour le PDF — Style fiscal EEBC (charte graphique + Cerfa)
    css = CSS(string='''
        @page {
            size: A4;
            margin: 1.2cm 1.4cm;
        }

        body {
            font-family: "Aptos", "Segoe UI", Arial, sans-serif;
            font-size: 9pt;
            line-height: 1.5;
            color: #132238;
            background: #ffffff;
        }

        /* ── Gold accent bar (top) ── */
        .gold-accent {
            height: 4px;
            border-radius: 999px;
            background: linear-gradient(90deg, #b8860b 0%, #d4a11e 45%, #f0c850 100%);
            margin-bottom: 0.35cm;
        }

        /* ── Header block ── */
        .header-block {
            display: flex;
            align-items: flex-start;
            gap: 0.4cm;
            margin-bottom: 0.4cm;
        }
        .header-logo {
            width: 2.2cm;
            height: 2.2cm;
            padding: 0.12cm;
            border-radius: 12px;
            border: 1px solid #dbe3ef;
            background: #ffffff;
            box-shadow: 0 4px 12px rgba(17, 46, 99, 0.08);
            flex-shrink: 0;
        }
        .header-logo img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .header-text {
            flex: 1;
            padding-top: 0.06cm;
            text-align: center;
        }
        .header-kicker {
            font-size: 7pt;
            font-weight: 700;
            color: #bf8c10;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            margin-bottom: 0.06cm;
        }
        .header-title {
            font-size: 14pt;
            font-weight: 800;
            color: #112e63;
            line-height: 1.1;
            margin-bottom: 0.06cm;
        }
        .header-subtitle {
            font-size: 8pt;
            color: #5b6b7d;
            letter-spacing: 0.04em;
        }
        .header-ref {
            font-size: 7pt;
            color: #8b97a8;
            margin-top: 0.04cm;
        }

        /* ── Receipt number panel ── */
        .receipt-panel {
            width: 4.8cm;
            padding: 0.32cm 0.38cm;
            border-radius: 14px;
            background: linear-gradient(135deg, #112e63 0%, #1d478f 100%);
            color: #ffffff;
            box-shadow: 0 8px 20px rgba(17, 46, 99, 0.16);
            flex-shrink: 0;
            text-align: center;
        }
        .panel-label {
            font-size: 7pt;
            font-weight: 700;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            opacity: 0.8;
        }
        .panel-number {
            font-family: "Consolas", "Courier New", monospace;
            font-size: 10pt;
            font-weight: 700;
            margin: 0.08cm 0;
        }
        .panel-year {
            font-size: 8pt;
            opacity: 0.75;
        }

        /* ── Type badge ── */
        .type-badge {
            display: inline-block;
            background: linear-gradient(135deg, #112e63, #1d478f);
            color: #ffffff;
            font-size: 7.5pt;
            font-weight: 700;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            padding: 3px 14px;
            border-radius: 999px;
            margin-bottom: 0.3cm;
        }

        /* ── Cadres ── */
        .cadre {
            border: 1px solid #d0d8e4;
            border-radius: 10px;
            margin-bottom: 0.28cm;
            overflow: hidden;
            box-shadow: 0 1px 4px rgba(17, 46, 99, 0.04);
        }
        .cadre-header {
            background: linear-gradient(135deg, #f0f4fa 0%, #e8edf5 100%);
            border-bottom: 1px solid #d0d8e4;
            padding: 5px 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .cadre-num {
            display: inline-block;
            width: 20px;
            height: 20px;
            background: linear-gradient(135deg, #112e63, #1d478f);
            color: #ffffff;
            font-weight: 700;
            font-size: 8.5pt;
            text-align: center;
            line-height: 20px;
            border-radius: 6px;
        }
        .cadre-title {
            font-size: 8pt;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #112e63;
        }
        .cadre-body {
            padding: 10px 14px;
        }

        /* ── Info tables ── */
        .info-table {
            width: 100%;
            border-collapse: collapse;
        }
        .info-table td {
            padding: 2.5px 0;
            vertical-align: top;
            font-size: 9pt;
        }
        .info-label {
            width: 100px;
            color: #5b6b7d;
        }
        .info-value {
            color: #132238;
        }

        /* ── Nature & checkboxes ── */
        .nature-organisme,
        .nature-checks,
        .nature-detail {
            margin-top: 6px;
            font-size: 9pt;
            color: #2d3e50;
        }

        /* ── Amount cadre ── */
        .cadre-amount {
            background: linear-gradient(135deg, #faf8f4 0%, #f5f0e8 100%);
            padding: 14px 18px;
        }
        .amount-row {
            display: flex;
            align-items: baseline;
            padding: 3px 0;
            font-size: 9pt;
        }
        .amount-label {
            width: 130px;
            color: #5b6b7d;
        }
        .amount-value {
            font-weight: 800;
            color: #112e63;
            font-family: "Consolas", "Courier New", monospace;
            letter-spacing: 0.03em;
        }
        .amount-words {
            color: #2d3e50;
        }
        .amount-gold-bar {
            height: 2px;
            margin-top: 8px;
            border-radius: 999px;
            background: linear-gradient(90deg, #b8860b 0%, #d4a11e 50%, #f0c850 100%);
            opacity: 0.5;
        }

        /* ── Versements table ── */
        .cadre-table-body { padding: 0; }
        .versements-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 8.5pt;
        }
        .versements-table th {
            background: linear-gradient(135deg, #f0f4fa, #e8edf5);
            border-bottom: 1px solid #d0d8e4;
            padding: 5px 12px;
            text-align: left;
            font-weight: 700;
            font-size: 7.5pt;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #112e63;
        }
        .versements-table td {
            padding: 4px 12px;
            border-bottom: 0.5px solid #e8edf5;
        }
        .versements-table tbody tr:nth-child(even) {
            background: #fafbfd;
        }
        .td-amount {
            text-align: right;
            font-family: "Consolas", "Courier New", monospace;
        }
        .col-date { width: 22%; }
        .col-type { width: 30%; }
        .col-mode { width: 24%; }
        .col-amount { width: 24%; text-align: right; }
        .total-row {
            background: linear-gradient(135deg, #112e63, #1d478f);
            color: #ffffff;
        }
        .total-row td {
            padding: 6px 12px;
            border: none;
            font-weight: 700;
        }

        /* ── Attestation ── */
        .cadre-attestation { margin-top: 0.12cm; }
        .attestation-text {
            font-size: 9pt;
            line-height: 1.5;
            margin: 0 0 10px 0;
            color: #2d3e50;
        }
        .signature-table {
            width: 100%;
            border-collapse: collapse;
        }
        .sig-cell {
            width: 50%;
            padding: 5px 0;
            vertical-align: top;
            font-size: 9pt;
            color: #5b6b7d;
        }
        .sig-right { text-align: right; }
        .sig-line {
            border-bottom: 1px solid #d0d8e4;
            height: 36px;
            margin-top: 6px;
            margin-left: 40%;
        }

        /* ── Legal block ── */
        .legal-block {
            margin-top: 0.25cm;
            padding: 10px 14px;
            background: #f8f9fb;
            border: 1px solid #e0e5ed;
            border-radius: 8px;
            font-size: 7.5pt;
            color: #5b6b7d;
            line-height: 1.5;
        }
        .legal-block p { margin: 0 0 4px 0; }

        /* ── Footer ── */
        .footer {
            margin-top: 0.3cm;
            text-align: center;
            font-size: 7pt;
            color: #8b97a8;
            padding-top: 8px;
        }
        .footer-gold {
            height: 2px;
            border-radius: 999px;
            background: linear-gradient(90deg, transparent, #d4a11e, #f0c850, #d4a11e, transparent);
            margin-bottom: 8px;
        }
    ''')
    
    # Générer le PDF
    html = HTML(string=html_content)
    pdf_bytes = html.write_pdf(stylesheets=[css])
    
    return pdf_bytes


def save_tax_receipt_pdf(tax_receipt):
    """
    Génère et sauvegarde le PDF d'un reçu fiscal.
    
    Args:
        tax_receipt: Instance de TaxReceipt
    """
    pdf_bytes = generate_tax_receipt_pdf(tax_receipt)
    
    # Nom du fichier
    filename = f"recu_fiscal_{tax_receipt.receipt_number}.pdf"
    
    # Sauvegarder dans le modèle
    tax_receipt.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
    
    return tax_receipt.pdf_file


# =============================================================================
# REÇU DE DON EN LIGNE (PDF professionnel)
# =============================================================================

def _get_logo_base64():
    """Récupère le logo de l'église en base64 (SiteSettings ou fallback EEBC/logo.png)."""
    # 1. Essayer le logo depuis SiteSettings
    try:
        from apps.core.models import SiteSettings
        site_settings = SiteSettings.objects.first()
        if site_settings and site_settings.logo:
            logo_path = Path(settings.MEDIA_ROOT) / str(site_settings.logo)
            if logo_path.exists():
                return base64.b64encode(logo_path.read_bytes()).decode('utf-8')
    except Exception:
        pass
    
    # 2. Fallback sur le logo EEBC du projet
    eebc_logo = Path(settings.BASE_DIR) / 'EEBC' / 'logo.png'
    if eebc_logo.exists():
        return base64.b64encode(eebc_logo.read_bytes()).decode('utf-8')
    
    # 3. Fallback sur le logo statique
    fallback = Path(settings.BASE_DIR) / 'static' / 'images' / 'eebc-logo.png'
    if fallback.exists():
        return base64.b64encode(fallback.read_bytes()).decode('utf-8')
    
    return ''


def _amount_to_words(amount):
    """Convertit un montant en toutes lettres (simplifié)."""
    units = ['', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf',
             'dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize']
    tens = ['', 'dix', 'vingt', 'trente', 'quarante', 'cinquante', 
            'soixante', 'soixante', 'quatre-vingt', 'quatre-vingt']

    def _convert_below_hundred(n):
        if n < 17:
            return units[n]
        elif n < 20:
            return f"dix-{units[n - 10]}"
        elif n < 70:
            t, u = divmod(n, 10)
            if u == 1 and t != 8:
                return f"{tens[t]} et un"
            return f"{tens[t]}-{units[u]}" if u else tens[t]
        elif n < 80:
            u = n - 60
            if u == 1:
                return "soixante et onze"
            return f"soixante-{_convert_below_hundred(u)}"
        else:
            u = n - 80
            base = "quatre-vingts" if u == 0 else f"quatre-vingt-{_convert_below_hundred(u)}"
            return base

    def _convert_below_thousand(n):
        if n < 100:
            return _convert_below_hundred(n)
        h, remainder = divmod(n, 100)
        prefix = "cent" if h == 1 else f"{units[h]} cent"
        if remainder == 0:
            return f"{prefix}s" if h > 1 else prefix
        return f"{prefix} {_convert_below_hundred(remainder)}"

    from decimal import Decimal
    amount = Decimal(str(amount))
    euros = int(amount)
    cents = int(round((amount - euros) * 100))

    if euros == 0:
        result = "zéro"
    elif euros == 1:
        result = "un"
    elif euros < 1000:
        result = _convert_below_thousand(euros)
    elif euros < 2000:
        remainder = euros - 1000
        result = f"mille {_convert_below_thousand(remainder)}" if remainder else "mille"
    else:
        thousands, remainder = divmod(euros, 1000)
        prefix = f"{_convert_below_thousand(thousands)} mille"
        result = f"{prefix} {_convert_below_thousand(remainder)}" if remainder else prefix

    result = f"{result} euro{'s' if euros != 1 else ''}"
    if cents:
        result += f" et {_convert_below_hundred(cents)} centime{'s' if cents != 1 else ''}"

    return result.capitalize()


def _format_amount_fr(amount):
    """Formate un montant au format francais 1 234,56."""
    normalized = Decimal(str(amount)).quantize(Decimal('0.01'))
    return f"{normalized:,.2f}".replace(',', ' ').replace('.', ',')


def _format_long_date_fr(value):
    """Formate une date francaise longue sans dependre des locales systeme."""
    from datetime import date as date_type
    if isinstance(value, date_type) and not hasattr(value, 'hour'):
        return f"{value.day} {FRENCH_MONTHS[value.month - 1]} {value.year}"
    dt_value = timezone.localtime(value) if timezone.is_aware(value) else value
    return f"{dt_value.day} {FRENCH_MONTHS[dt_value.month - 1]} {dt_value.year}"


def _format_datetime_fr(value):
    """Formate une date/heure francaise courte."""
    dt_value = timezone.localtime(value) if timezone.is_aware(value) else value
    return dt_value.strftime('%d/%m/%Y a %H:%M')


@lru_cache(maxsize=1)
def _get_donation_receipt_jinja_env():
    """Construit l'environnement Jinja2 dedie aux PDF corporate finance."""
    try:
        from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
    except ImportError as exc:
        raise ImportError("Jinja2 n'est pas installe. pip install Jinja2") from exc

    return Environment(
        loader=FileSystemLoader(str(DONATION_RECEIPT_TEMPLATE_DIR)),
        autoescape=select_autoescape(['html', 'xml']),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )


def _render_donation_receipt_template(template_name, context):
    """Rend un gabarit Jinja2 pour les recus de don."""
    return _get_donation_receipt_jinja_env().get_template(template_name).render(**context)


def _get_member_address_line(member):
    """Construit la ligne d'adresse a partir d'un membre."""
    if not member:
        return ''
    parts = [
        getattr(member, 'address', '') or '',
        ' '.join(filter(None, [getattr(member, 'postal_code', ''), getattr(member, 'city', '')])),
    ]
    return ', '.join(p for p in parts if p.strip())


def _build_donation_receipt_context(online_donation, receipt_number):
    """Prepare le contexte du recu de don pour Jinja2."""
    issue_date = timezone.now()
    donation_date = online_donation.created_at
    member_name = online_donation.member.get_full_name() if online_donation.member else ''
    donor_name = online_donation.donor_name or member_name or online_donation.donor_email or 'Donateur'
    donor_secondary_line = (
        online_donation.donor_email
        if online_donation.donor_email and online_donation.donor_email != donor_name
        else ''
    )
    reference = online_donation.transaction.reference if online_donation.transaction else ''
    logo_base64 = _get_logo_base64()
    recurring_note = ''

    if online_donation.is_recurring:
        recurring_note = (
            'Don recurrent mensuel - renouvellement automatique chaque mois.'
            if online_donation.recurring_interval == 'month'
            else 'Don recurrent annuel - renouvellement automatique chaque annee.'
        )

    type_labels = {
        'don': 'Don',
        'dime': 'Dime',
        'offrande': 'Offrande',
    }

    church_contact_line = ' • '.join(
        part for part in [CHURCH_INFO['phone'], CHURCH_INFO['email']] if part
    )
    church_registration_line = ' • '.join(
        part
        for part in [
            f"SIRET {CHURCH_INFO['siret']}" if CHURCH_INFO['siret'] else '',
            f"RNA {CHURCH_INFO['rna']}" if CHURCH_INFO['rna'] else '',
        ]
        if part
    )

    return {
        'receipt_number': receipt_number,
        'logo_data_uri': f"data:image/png;base64,{logo_base64}" if logo_base64 else '',
        'church_name': CHURCH_INFO['name'],
        'church_address': CHURCH_INFO['address'],
        'church_contact_line': church_contact_line,
        'church_registration_line': church_registration_line,
        'issue_city': os.environ.get('CHURCH_CITY', 'Cayenne'),
        'issue_date_long': _format_long_date_fr(issue_date),
        'donor_display_name': donor_name,
        'donor_address_line': _get_member_address_line(online_donation.member),
        'donor_secondary_line': donor_secondary_line,
        'member_name': member_name,
        'donation_date_display': _format_datetime_fr(donation_date),
        'donation_type_display': type_labels.get(online_donation.donation_type, 'Don'),
        'reference': reference,
        'payment_method_display': 'Carte bancaire (Stripe)',
        'amount_display': _format_amount_fr(online_donation.amount),
        'amount_words': _amount_to_words(online_donation.amount),
        'recurring_note': recurring_note,
        'generation_date_display': _format_datetime_fr(issue_date),
    }


def generate_donation_receipt_pdf(online_donation):
    """
    Génère un PDF de reçu professionnel pour un don en ligne.
    
    Args:
        online_donation: Instance de OnlineDonation
    
    Returns:
        bytes: Contenu du PDF
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        raise ImportError("WeasyPrint n'est pas installé. pip install weasyprint")

    receipt_number = f"DON-{online_donation.created_at.strftime('%Y%m')}-{online_donation.id:05d}"
    context = _build_donation_receipt_context(online_donation, receipt_number)
    html_content = _render_donation_receipt_template('donation_receipt.html.j2', context)
    css_path = DONATION_RECEIPT_TEMPLATE_DIR / 'donation_receipt.css'

    html = HTML(string=html_content, base_url=str(settings.BASE_DIR))
    css = CSS(filename=str(css_path))
    pdf_bytes = html.write_pdf(stylesheets=[css])

    logger.info(f"Donation receipt PDF generated: {receipt_number}")
    return pdf_bytes, receipt_number


def generate_transaction_receipt_pdf(transaction):
    """
    Génère un PDF de reçu pour une transaction manuelle (espèces, chèque, virement…).

    Args:
        transaction: Instance de FinancialTransaction (don/dîme/offrande)

    Returns:
        tuple: (pdf_bytes, receipt_number)
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        raise ImportError("WeasyPrint n'est pas installé. pip install weasyprint")

    receipt_number = f"DON-{transaction.transaction_date.strftime('%Y%m')}-{transaction.id:05d}"

    issue_date = timezone.now()
    donation_date = transaction.transaction_date

    member_name = transaction.member.get_full_name() if transaction.member else ''
    donor_name = member_name or transaction.description or 'Donateur'
    donor_secondary_line = ''
    donor_address_line = _get_member_address_line(transaction.member)

    logo_base64 = _get_logo_base64()

    type_labels = {
        'don': 'Don',
        'dime': 'Dîme',
        'offrande': 'Offrande',
    }

    payment_labels = {
        'especes': 'Espèces',
        'cheque': 'Chèque',
        'virement': 'Virement bancaire',
        'carte': 'Carte bancaire',
        'mobile': 'Paiement mobile',
        'autre': 'Autre',
    }

    church_contact_line = ' • '.join(
        part for part in [CHURCH_INFO['phone'], CHURCH_INFO['email']] if part
    )
    church_registration_line = ' • '.join(
        part
        for part in [
            f"SIRET {CHURCH_INFO['siret']}" if CHURCH_INFO['siret'] else '',
            f"RNA {CHURCH_INFO['rna']}" if CHURCH_INFO['rna'] else '',
        ]
        if part
    )

    context = {
        'receipt_number': receipt_number,
        'logo_data_uri': f"data:image/png;base64,{logo_base64}" if logo_base64 else '',
        'church_name': CHURCH_INFO['name'],
        'church_address': CHURCH_INFO['address'],
        'church_contact_line': church_contact_line,
        'church_registration_line': church_registration_line,
        'issue_city': os.environ.get('CHURCH_CITY', 'Cayenne'),
        'issue_date_long': _format_long_date_fr(issue_date),
        'donor_display_name': donor_name,
        'donor_address_line': donor_address_line,
        'donor_secondary_line': donor_secondary_line,
        'member_name': member_name,
        'donation_date_display': _format_long_date_fr(donation_date),
        'donation_type_display': type_labels.get(transaction.transaction_type, 'Don'),
        'payment_method_display': payment_labels.get(transaction.payment_method, 'Espèces'),
        'reference': transaction.reference,
        'amount_display': _format_amount_fr(transaction.amount),
        'amount_words': _amount_to_words(transaction.amount),
        'recurring_note': '',
        'generation_date_display': _format_datetime_fr(issue_date),
    }

    html_content = _render_donation_receipt_template('donation_receipt.html.j2', context)
    css_path = DONATION_RECEIPT_TEMPLATE_DIR / 'donation_receipt.css'

    html = HTML(string=html_content, base_url=str(settings.BASE_DIR))
    css = CSS(filename=str(css_path))
    pdf_bytes = html.write_pdf(stylesheets=[css])

    logger.info(f"Transaction receipt PDF generated: {receipt_number} (transaction #{transaction.id})")
    return pdf_bytes, receipt_number


def generate_campaign_donation_receipt_pdf(donation):
    """
    Génère un PDF de reçu pour un don de campagne.

    Args:
        donation: Instance de campaigns.Donation

    Returns:
        tuple: (pdf_bytes, receipt_number)
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        raise ImportError("WeasyPrint n'est pas installé. pip install weasyprint")

    receipt_number = f"DON-{donation.donation_date.strftime('%Y%m')}-C{donation.id:05d}"

    issue_date = timezone.now()
    donor_name = 'Anonyme' if donation.is_anonymous else (donation.donor_name or 'Donateur')
    logo_base64 = _get_logo_base64()

    church_contact_line = ' • '.join(
        part for part in [CHURCH_INFO['phone'], CHURCH_INFO['email']] if part
    )
    church_registration_line = ' • '.join(
        part
        for part in [
            f"SIRET {CHURCH_INFO['siret']}" if CHURCH_INFO['siret'] else '',
            f"RNA {CHURCH_INFO['rna']}" if CHURCH_INFO['rna'] else '',
        ]
        if part
    )

    context = {
        'receipt_number': receipt_number,
        'logo_data_uri': f"data:image/png;base64,{logo_base64}" if logo_base64 else '',
        'church_name': CHURCH_INFO['name'],
        'church_address': CHURCH_INFO['address'],
        'church_contact_line': church_contact_line,
        'church_registration_line': church_registration_line,
        'issue_city': os.environ.get('CHURCH_CITY', 'Cayenne'),
        'issue_date_long': _format_long_date_fr(issue_date),
        'donor_display_name': donor_name,
        'donor_address_line': '',
        'donor_secondary_line': f"Campagne : {donation.campaign.name}",
        'member_name': '',
        'donation_date_display': _format_long_date_fr(donation.donation_date),
        'donation_type_display': 'Don',
        'payment_method_display': 'Espèces',
        'reference': receipt_number,
        'amount_display': _format_amount_fr(donation.amount),
        'amount_words': _amount_to_words(donation.amount),
        'recurring_note': '',
        'generation_date_display': _format_datetime_fr(issue_date),
    }

    html_content = _render_donation_receipt_template('donation_receipt.html.j2', context)
    css_path = DONATION_RECEIPT_TEMPLATE_DIR / 'donation_receipt.css'

    html = HTML(string=html_content, base_url=str(settings.BASE_DIR))
    css = CSS(filename=str(css_path))
    pdf_bytes = html.write_pdf(stylesheets=[css])

    logger.info(f"Campaign donation receipt PDF generated: {receipt_number} (donation #{donation.id})")
    return pdf_bytes, receipt_number


def generate_manual_donation_receipt_pdf(donor_name, donor_address, donor_email,
                                         amount, donation_type, payment_method,
                                         donation_date):
    """
    Génère un PDF de reçu de don à partir des informations saisies manuellement.

    Returns:
        tuple: (pdf_bytes, receipt_number)
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        raise ImportError("WeasyPrint n'est pas installé. pip install weasyprint")

    import random
    receipt_id = random.randint(10000, 99999)
    receipt_number = f"DON-{donation_date.strftime('%Y%m')}-M{receipt_id:05d}"

    issue_date = timezone.now()
    logo_base64 = _get_logo_base64()

    type_labels = {'don': 'Don', 'dime': 'Dîme', 'offrande': 'Offrande'}
    payment_labels = {
        'especes': 'Espèces', 'cheque': 'Chèque', 'virement': 'Virement bancaire',
        'carte': 'Carte bancaire', 'mobile': 'Paiement mobile', 'autre': 'Autre',
    }

    church_contact_line = ' • '.join(
        part for part in [CHURCH_INFO['phone'], CHURCH_INFO['email']] if part
    )
    church_registration_line = ' • '.join(
        part
        for part in [
            f"SIRET {CHURCH_INFO['siret']}" if CHURCH_INFO['siret'] else '',
            f"RNA {CHURCH_INFO['rna']}" if CHURCH_INFO['rna'] else '',
        ]
        if part
    )

    context = {
        'receipt_number': receipt_number,
        'logo_data_uri': f"data:image/png;base64,{logo_base64}" if logo_base64 else '',
        'church_name': CHURCH_INFO['name'],
        'church_address': CHURCH_INFO['address'],
        'church_contact_line': church_contact_line,
        'church_registration_line': church_registration_line,
        'issue_city': os.environ.get('CHURCH_CITY', 'Cayenne'),
        'issue_date_long': _format_long_date_fr(issue_date),
        'donor_display_name': donor_name,
        'donor_address_line': donor_address,
        'donor_secondary_line': donor_email,
        'member_name': '',
        'donation_date_display': _format_long_date_fr(donation_date),
        'donation_type_display': type_labels.get(donation_type, 'Don'),
        'payment_method_display': payment_labels.get(payment_method, 'Espèces'),
        'reference': receipt_number,
        'amount_display': _format_amount_fr(amount),
        'amount_words': _amount_to_words(amount),
        'recurring_note': '',
        'generation_date_display': _format_datetime_fr(issue_date),
    }

    html_content = _render_donation_receipt_template('donation_receipt.html.j2', context)
    css_path = DONATION_RECEIPT_TEMPLATE_DIR / 'donation_receipt.css'

    html = HTML(string=html_content, base_url=str(settings.BASE_DIR))
    css = CSS(filename=str(css_path))
    pdf_bytes = html.write_pdf(stylesheets=[css])

    logger.info(f"Manual donation receipt PDF generated: {receipt_number}")
    return pdf_bytes, receipt_number


def number_to_words_fr(number):
    """Convertit un nombre en lettres (français)."""
    units = ['', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf',
             'dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize', 'dix-sept',
             'dix-huit', 'dix-neuf']
    tens = ['', '', 'vingt', 'trente', 'quarante', 'cinquante', 'soixante', 
            'soixante', 'quatre-vingt', 'quatre-vingt']
    
    def convert_less_than_hundred(n):
        if n < 20:
            return units[n]
        elif n < 70:
            unit = n % 10
            ten = n // 10
            if unit == 0:
                return tens[ten]
            elif unit == 1 and ten != 8:
                return f"{tens[ten]} et un"
            else:
                return f"{tens[ten]}-{units[unit]}"
        elif n < 80:
            unit = n - 60
            return f"soixante-{units[unit]}" if unit != 11 else "soixante et onze"
        else:
            unit = n - 80
            if unit == 0:
                return "quatre-vingts"
            else:
                return f"quatre-vingt-{units[unit]}"
    
    def convert_less_than_thousand(n):
        if n < 100:
            return convert_less_than_hundred(n)
        else:
            hundreds = n // 100
            remainder = n % 100
            if hundreds == 1:
                prefix = "cent"
            else:
                prefix = f"{units[hundreds]} cent"
            
            if remainder == 0:
                return prefix + ("s" if hundreds > 1 else "")
            else:
                return f"{prefix} {convert_less_than_hundred(remainder)}"
    
    if number == 0:
        return "zéro"
    
    # Séparer euros et centimes
    euros = int(number)
    centimes = int(round((number - euros) * 100))
    
    result = ""
    
    if euros >= 1000:
        thousands = euros // 1000
        euros = euros % 1000
        if thousands == 1:
            result = "mille"
        else:
            result = f"{convert_less_than_thousand(thousands)} mille"
    
    if euros > 0:
        if result:
            result += " "
        result += convert_less_than_thousand(euros)
    
    result += " euro" + ("s" if int(number) > 1 else "")
    
    if centimes > 0:
        result += f" et {convert_less_than_hundred(centimes)} centime"
        result += "s" if centimes > 1 else ""
    
    return result.strip()
