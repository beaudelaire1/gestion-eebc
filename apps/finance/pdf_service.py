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
    }
    
    # Rendre le template HTML
    html_content = render_to_string('finance/tax_receipt_pdf.html', context)
    
    # CSS pour le PDF
    css = CSS(string='''
        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #1e293b;
        }

        .gold-border-top {
            height: 4px;
            background: linear-gradient(90deg, #b8860b, #daa520, #f0c850, #daa520, #b8860b);
            margin-bottom: 25px;
            border-radius: 2px;
        }

        .gold-border-bottom {
            height: 4px;
            background: linear-gradient(90deg, #b8860b, #daa520, #f0c850, #daa520, #b8860b);
            margin-top: 20px;
            border-radius: 2px;
        }

        .header {
            text-align: center;
            margin-bottom: 25px;
            border-bottom: 2px solid #0f2557;
            padding-bottom: 20px;
        }

        .header-logo {
            width: 80px;
            height: 80px;
            object-fit: contain;
            margin-bottom: 10px;
        }

        .header h1 {
            color: #0f2557;
            font-size: 18pt;
            font-weight: 800;
            margin: 0;
            letter-spacing: 0.5px;
        }

        .header h2 {
            font-size: 12pt;
            color: #daa520;
            margin: 8px 0 0 0;
            text-transform: uppercase;
            letter-spacing: 3px;
            font-weight: 700;
        }

        .header-legal-ref {
            font-size: 9pt;
            color: #64748b;
            margin-top: 4px;
            font-style: italic;
        }

        .receipt-number {
            text-align: right;
            font-size: 12pt;
            color: #0f2557;
            font-weight: bold;
            margin-bottom: 20px;
            font-family: "Courier New", monospace;
        }

        .section {
            margin-bottom: 25px;
        }

        .section-title {
            font-weight: 700;
            color: #0f2557;
            border-bottom: 2px solid #0f2557;
            padding-bottom: 6px;
            margin-bottom: 12px;
            text-transform: uppercase;
            font-size: 9pt;
            letter-spacing: 2px;
        }

        .info-row {
            display: flex;
            margin-bottom: 5px;
        }

        .info-label {
            width: 150px;
            font-weight: bold;
        }

        .amount-box {
            background: linear-gradient(135deg, #0f2557 0%, #1a3a6b 100%);
            border-radius: 8px;
            padding: 25px;
            text-align: center;
            margin: 30px 0;
            color: #ffffff;
        }

        .amount-box .amount {
            font-size: 28pt;
            font-weight: 900;
            color: #ffffff;
        }

        .amount-box .amount-text {
            font-size: 11pt;
            color: #cbd5e1;
            margin-top: 6px;
            font-style: italic;
        }

        .legal-text {
            font-size: 8.5pt;
            color: #64748b;
            border: 1px solid #e2e8f0;
            padding: 15px 18px;
            margin-top: 30px;
            background: #f8fafc;
            border-radius: 4px;
            line-height: 1.6;
        }

        .signature-section {
            margin-top: 40px;
            display: flex;
            justify-content: space-between;
        }

        .signature-box {
            width: 45%;
        }

        .signature-line {
            border-bottom: 1px solid #1e293b;
            height: 60px;
            margin-top: 10px;
        }

        .footer {
            margin-top: 40px;
            text-align: center;
            font-size: 8.5pt;
            color: #94a3b8;
        }

        .footer-line-tax {
            height: 1px;
            background: linear-gradient(90deg, transparent, #cbd5e1, transparent);
            margin-bottom: 12px;
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
        'donor_secondary_line': donor_secondary_line,
        'member_name': member_name,
        'donation_date_display': _format_datetime_fr(donation_date),
        'donation_type_display': type_labels.get(online_donation.donation_type, 'Don'),
        'reference': reference,
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
