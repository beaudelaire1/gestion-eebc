"""
Service de génération PDF pour les reçus fiscaux.

Utilise WeasyPrint pour générer des PDF conformes.
"""

import io
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.conf import settings


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
        'church_name': "Église Évangélique Baptiste de Cabassou",
        'church_address': "5 rue Calimbés 2, Route de Cabassou, 97300 Cayenne",
        'church_siret': "XXX XXX XXX XXXXX",  # À configurer
        'church_rna': "W9XXXXXXXX",  # Numéro RNA
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
