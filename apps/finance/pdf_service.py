"""
Service de génération PDF pour les reçus fiscaux et reçus de dons.

Utilise WeasyPrint pour générer des PDF conformes.
"""

import io
import os
import logging
import base64
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
    """Récupère le logo de l'église en base64 (SiteSettings ou fallback EEBC/logo1.png)."""
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
    eebc_logo = Path(settings.BASE_DIR) / 'EEBC' / 'logo1.png'
    if eebc_logo.exists():
        return base64.b64encode(eebc_logo.read_bytes()).decode('utf-8')
    
    # 3. Fallback sur l'icône PWA
    fallback = Path(settings.BASE_DIR) / 'static' / 'icons' / 'icon-192x192.png'
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

    # Numéro de reçu basé sur l'ID et la date
    receipt_number = f"DON-{online_donation.created_at.strftime('%Y%m')}-{online_donation.id:05d}"

    # Nom du donateur
    donor_name = online_donation.donor_name or ''
    if not donor_name and online_donation.member:
        donor_name = online_donation.member.get_full_name()
    
    # Référence transaction
    reference = ''
    if online_donation.transaction:
        reference = online_donation.transaction.reference

    # Type de don lisible
    type_labels = {
        'don': 'Don',
        'dime': 'Dîme',
        'offrande': 'Offrande',
    }

    # Charger le logo en base64
    logo_base64 = _get_logo_base64()

    context = {
        'receipt_number': receipt_number,
        'logo_base64': logo_base64,
        'church_name': CHURCH_INFO['name'],
        'church_address': CHURCH_INFO['address'],
        'church_phone': CHURCH_INFO['phone'],
        'church_email': CHURCH_INFO['email'],
        'donor_name': donor_name,
        'donor_email': online_donation.donor_email,
        'member_name': online_donation.member.get_full_name() if online_donation.member else '',
        'amount': online_donation.amount,
        'amount_words': _amount_to_words(online_donation.amount),
        'donation_type_display': type_labels.get(online_donation.donation_type, 'Don'),
        'donation_date': online_donation.created_at,
        'reference': reference,
        'is_recurring': online_donation.is_recurring,
        'recurring_interval': online_donation.recurring_interval,
        'issue_date': timezone.now(),
        'generation_date': timezone.now(),
    }

    html_content = render_to_string('finance/donation_receipt_pdf.html', context)

    css = CSS(string='''
        @page {
            size: A4;
            margin: 1.8cm 2cm;

            @bottom-center {
                content: "";
            }
        }

        body {
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 10.5pt;
            line-height: 1.6;
            color: #1e293b;
            position: relative;
        }

        /* ── Filigrane ───────────────────────── */
        .watermark {
            position: fixed;
            top: 35%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 160pt;
            font-weight: 900;
            color: rgba(26, 58, 107, 0.03);
            letter-spacing: 20px;
            z-index: -1;
            pointer-events: none;
        }

        /* ── Bordures dorées ─────────────────── */
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

        /* ── En-tête ─────────────────────────── */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }

        .logo-area {
            display: flex;
            align-items: flex-start;
            gap: 16px;
        }

        .church-logo {
            width: 70px;
            height: 70px;
            border-radius: 6px;
            object-fit: contain;
        }

        .church-name {
            font-size: 14pt;
            font-weight: 800;
            color: #0f2557;
            letter-spacing: 0.3px;
            margin-bottom: 2px;
        }

        .church-subtitle {
            font-size: 8pt;
            color: #b8860b;
            text-transform: uppercase;
            letter-spacing: 2.5px;
            font-weight: 600;
            margin-bottom: 6px;
        }

        .church-address-line {
            font-size: 8.5pt;
            color: #64748b;
            line-height: 1.4;
        }

        .church-contact {
            font-size: 8pt;
            color: #94a3b8;
        }

        .header-right {
            text-align: right;
            padding-top: 4px;
        }

        .receipt-badge {
            background: linear-gradient(135deg, #0f2557, #1a3a6b);
            color: #ffffff;
            padding: 8px 20px;
            border-radius: 4px;
            display: inline-block;
            margin-bottom: 8px;
        }

        .receipt-label {
            font-size: 11pt;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        .receipt-number {
            font-size: 10pt;
            color: #0f2557;
            font-weight: 700;
            font-family: "Courier New", monospace;
        }

        .receipt-date {
            font-size: 9pt;
            color: #64748b;
            margin-top: 4px;
            font-style: italic;
        }

        .header-line {
            height: 2px;
            background: linear-gradient(90deg, #0f2557 0%, #1a3a6b 40%, #daa520 60%, #f0c850 100%);
            margin-bottom: 25px;
            border-radius: 1px;
        }

        /* ── Colonnes ────────────────────────── */
        .columns {
            display: flex;
            gap: 30px;
            margin-bottom: 25px;
        }

        .col-left, .col-right {
            flex: 1;
        }

        .section-title {
            font-size: 8pt;
            font-weight: 700;
            color: #0f2557;
            text-transform: uppercase;
            letter-spacing: 2px;
            border-bottom: 2px solid #0f2557;
            padding-bottom: 6px;
            margin-bottom: 14px;
        }

        .section-icon {
            color: #daa520;
            font-size: 6pt;
            margin-right: 4px;
        }

        .donor-card {
            background: #f8fafc;
            border-left: 3px solid #0f2557;
            padding: 12px 16px;
            border-radius: 0 4px 4px 0;
        }

        .donor-name {
            font-size: 12pt;
            font-weight: 700;
            color: #0f2557;
            margin-bottom: 4px;
        }

        .donor-email {
            font-size: 9.5pt;
            color: #64748b;
        }

        .detail-card {
            background: #f8fafc;
            border-left: 3px solid #daa520;
            padding: 8px 16px;
            border-radius: 0 4px 4px 0;
        }

        .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid #e2e8f0;
        }

        .detail-row:last-child {
            border-bottom: none;
        }

        .detail-label {
            font-size: 9pt;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .detail-value {
            font-weight: 600;
            font-size: 10pt;
            color: #1e293b;
        }

        .detail-mono {
            font-family: "Courier New", monospace;
            font-size: 9pt;
        }

        /* ── Montant ─────────────────────────── */
        .amount-section {
            margin: 25px 0;
        }

        .amount-box {
            background: linear-gradient(135deg, #0f2557 0%, #1a3a6b 100%);
            border-radius: 8px;
            padding: 28px 30px;
            text-align: center;
            color: #ffffff;
            position: relative;
        }

        .amount-label {
            font-size: 8pt;
            text-transform: uppercase;
            letter-spacing: 3px;
            color: #daa520;
            margin-bottom: 10px;
            font-weight: 600;
        }

        .amount-value {
            font-size: 34pt;
            font-weight: 900;
            color: #ffffff;
            letter-spacing: 2px;
        }

        .currency {
            font-size: 22pt;
            font-weight: 400;
        }

        .amount-divider {
            width: 60px;
            height: 2px;
            background: #daa520;
            margin: 12px auto;
            border-radius: 1px;
        }

        .amount-words {
            font-size: 10pt;
            color: #cbd5e1;
            font-style: italic;
            letter-spacing: 0.5px;
        }

        /* ── Statut ──────────────────────────── */
        .status-box {
            background: #f0fdf4;
            border: 1px solid #86efac;
            border-radius: 6px;
            padding: 14px 20px;
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 18px;
        }

        .status-check {
            width: 32px;
            height: 32px;
            background: #16a34a;
            border-radius: 50%;
            color: #ffffff;
            font-size: 16pt;
            font-weight: bold;
            text-align: center;
            line-height: 32px;
            flex-shrink: 0;
        }

        .status-title {
            font-size: 10.5pt;
            color: #16a34a;
            font-weight: 700;
        }

        .status-detail {
            font-size: 8.5pt;
            color: #4ade80;
            margin-top: 2px;
        }

        /* ── Récurrent ───────────────────────── */
        .recurring-info {
            background: #fffbeb;
            border: 1px solid #fbbf24;
            border-radius: 6px;
            padding: 12px 20px;
            font-size: 9.5pt;
            color: #92400e;
            margin-bottom: 18px;
        }

        /* ── Citation ────────────────────────── */
        .spiritual-box {
            text-align: center;
            margin: 28px 30px;
            padding: 20px 25px;
            position: relative;
        }

        .verse-decoration {
            font-size: 36pt;
            color: #daa520;
            font-family: Georgia, serif;
            line-height: 1;
            margin-bottom: 4px;
            opacity: 0.7;
        }

        .verse {
            font-family: Georgia, "Times New Roman", serif;
            font-style: italic;
            font-size: 10.5pt;
            color: #334155;
            line-height: 2;
        }

        .verse-ref {
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 8.5pt;
            color: #daa520;
            margin-top: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        /* ── Mentions légales ────────────────── */
        .legal-text {
            font-size: 8pt;
            color: #64748b;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 14px 18px;
            margin-top: 20px;
            line-height: 1.5;
        }

        /* ── Pied de page ────────────────────── */
        .footer {
            margin-top: 30px;
            text-align: center;
        }

        .footer-line {
            height: 1px;
            background: linear-gradient(90deg, transparent, #cbd5e1, transparent);
            margin-bottom: 15px;
        }

        .footer-org {
            font-size: 9pt;
            font-weight: 700;
            color: #0f2557;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .footer-address {
            font-size: 8.5pt;
            color: #64748b;
            margin: 2px 0;
        }

        .footer-contacts {
            font-size: 8pt;
            color: #94a3b8;
        }

        .footer-generated {
            font-size: 7pt;
            color: #cbd5e1;
            margin-top: 10px;
            letter-spacing: 0.5px;
        }
    ''')

    html = HTML(string=html_content)
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
