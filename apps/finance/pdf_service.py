"""
Service de génération PDF pour les reçus fiscaux et reçus de dons.

Utilise WeasyPrint pour générer des PDF conformes.
"""

import io
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
    'name': "Église Évangélique Baptiste de Cabassou",
    'address': "5 rue Calimbés 2, Route de Cabassou, 97300 Cayenne",
    'phone': "",  # À configurer
    'email': "contact@eglise-ebc.org",
    'siret': "",  # À configurer
    'rna': "",  # À configurer
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
    
    # Contexte pour le template
    context = {
        'receipt': tax_receipt,
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
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #333;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #0A36FF;
            padding-bottom: 20px;
        }
        
        .header h1 {
            color: #0A36FF;
            font-size: 18pt;
            margin: 0;
        }
        
        .header h2 {
            font-size: 14pt;
            color: #666;
            margin: 10px 0 0 0;
        }
        
        .receipt-number {
            text-align: right;
            font-size: 12pt;
            color: #0A36FF;
            font-weight: bold;
            margin-bottom: 20px;
        }
        
        .section {
            margin-bottom: 25px;
        }
        
        .section-title {
            font-weight: bold;
            color: #0A36FF;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
            margin-bottom: 10px;
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
            background: #f5f5f5;
            border: 2px solid #0A36FF;
            padding: 20px;
            text-align: center;
            margin: 30px 0;
        }
        
        .amount-box .amount {
            font-size: 24pt;
            font-weight: bold;
            color: #0A36FF;
        }
        
        .amount-box .amount-text {
            font-size: 12pt;
            color: #666;
            margin-top: 5px;
        }
        
        .legal-text {
            font-size: 9pt;
            color: #666;
            border: 1px solid #ddd;
            padding: 15px;
            margin-top: 30px;
            background: #fafafa;
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
            border-bottom: 1px solid #333;
            height: 60px;
            margin-top: 10px;
        }
        
        .footer {
            margin-top: 50px;
            text-align: center;
            font-size: 9pt;
            color: #999;
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
    """Récupère le logo de l'église en base64 (SiteSettings ou fallback icône PWA)."""
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
    
    # 2. Fallback sur l'icône PWA
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
            margin: 2cm 2.5cm;
        }

        body {
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 10.5pt;
            line-height: 1.6;
            color: #2c2c2c;
        }

        /* ── En-tête ─────────────────────────── */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 8px;
        }

        .logo-area {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .church-logo {
            width: 55px;
            height: 55px;
            border-radius: 8px;
        }

        .church-name {
            font-size: 16pt;
            font-weight: 700;
            color: #1a3a6b;
            letter-spacing: 0.3px;
        }

        .church-subtitle {
            font-size: 9pt;
            color: #7a8a9e;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-top: 2px;
        }

        .header-right {
            text-align: right;
        }

        .receipt-label {
            font-size: 13pt;
            font-weight: 700;
            color: #1a3a6b;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .receipt-number {
            font-size: 10pt;
            color: #5a6a7e;
            margin-top: 2px;
        }

        .header-line {
            height: 3px;
            background: linear-gradient(90deg, #1a3a6b, #3a7bd5);
            margin-bottom: 20px;
            border-radius: 2px;
        }

        /* ── Infos église ────────────────────── */
        .church-info {
            font-size: 9pt;
            color: #6a7a8e;
            margin-bottom: 25px;
        }

        .church-info p { margin: 0; }

        /* ── Date ────────────────────────────── */
        .issue-date {
            text-align: right;
            font-size: 10pt;
            color: #4a5a6e;
            margin-bottom: 30px;
            font-style: italic;
        }

        /* ── Colonnes ────────────────────────── */
        .columns {
            display: flex;
            gap: 40px;
            margin-bottom: 30px;
        }

        .col-left, .col-right {
            flex: 1;
        }

        .section-title {
            font-size: 8.5pt;
            font-weight: 700;
            color: #1a3a6b;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            border-bottom: 1.5px solid #d0d8e4;
            padding-bottom: 6px;
            margin-bottom: 12px;
        }

        .donor-info {
            font-size: 10.5pt;
            line-height: 1.7;
        }

        .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            border-bottom: 1px dotted #e4e8ee;
        }

        .detail-label {
            font-size: 9.5pt;
            color: #6a7a8e;
        }

        .detail-value {
            font-weight: 600;
            font-size: 10pt;
        }

        /* ── Montant ─────────────────────────── */
        .amount-box {
            background: #f4f7fb;
            border: 2px solid #1a3a6b;
            border-radius: 6px;
            padding: 25px;
            text-align: center;
            margin: 30px 0;
        }

        .amount-label {
            font-size: 8.5pt;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: #6a7a8e;
            margin-bottom: 8px;
        }

        .amount-value {
            font-size: 28pt;
            font-weight: 800;
            color: #1a3a6b;
            letter-spacing: 1px;
        }

        .amount-words {
            font-size: 9.5pt;
            color: #5a6a7e;
            margin-top: 6px;
            font-style: italic;
        }

        /* ── Statut ──────────────────────────── */
        .status-box {
            background: #eafbf0;
            border: 1px solid #a8e6c3;
            border-radius: 4px;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 20px;
        }

        .status-icon {
            font-size: 16pt;
            color: #27ae60;
            font-weight: bold;
        }

        .status-text {
            font-size: 10pt;
            color: #27ae60;
            font-weight: 600;
        }

        /* ── Récurrent ───────────────────────── */
        .recurring-info {
            background: #fef9e7;
            border: 1px solid #f0d76e;
            border-radius: 4px;
            padding: 12px 20px;
            font-size: 9.5pt;
            color: #7d6608;
            margin-bottom: 20px;
        }

        /* ── Citation ────────────────────────── */
        .spiritual-box {
            text-align: center;
            margin: 30px 20px;
            padding: 20px;
        }

        .verse {
            font-style: italic;
            font-size: 10.5pt;
            color: #4a5a6e;
            line-height: 1.8;
        }

        .verse-ref {
            font-size: 9pt;
            color: #8a9aae;
            margin-top: 8px;
        }

        /* ── Mentions légales ────────────────── */
        .legal-text {
            font-size: 8.5pt;
            color: #7a8a9e;
            background: #f9fafb;
            border: 1px solid #e4e8ee;
            border-radius: 4px;
            padding: 14px 18px;
            margin-top: 20px;
        }

        /* ── Pied de page ────────────────────── */
        .footer {
            margin-top: 40px;
            text-align: center;
            font-size: 8.5pt;
            color: #9aaabe;
        }

        .footer-line {
            height: 1px;
            background: #d0d8e4;
            margin-bottom: 15px;
        }

        .footer p { margin: 0 0 4px 0; }

        .footer-legal {
            font-size: 7.5pt;
            color: #b0b8c8;
            margin-top: 8px;
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
