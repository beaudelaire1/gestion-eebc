"""
Service de génération PDF avec WeasyPrint.

Ce module fournit des fonctions pour générer des PDF à partir de templates HTML.
"""

from django.template.loader import render_to_string
from django.http import HttpResponse
from django.conf import settings
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PDFService:
    """Service de génération PDF avec WeasyPrint."""
    
    # CSS de base pour tous les PDF
    BASE_CSS = """
    @page {
        size: A4;
        margin: 15mm;
        @bottom-center {
            content: "Page " counter(page) " / " counter(pages);
            font-size: 9pt;
            color: #666;
        }
    }
    
    body {
        font-family: 'Helvetica', 'Arial', sans-serif;
        font-size: 10pt;
        line-height: 1.4;
        color: #333;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #366092;
        margin-top: 0;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
    }
    
    th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    
    th {
        background-color: #366092;
        color: white;
        font-weight: bold;
    }
    
    tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    
    .header {
        text-align: center;
        border-bottom: 2px solid #366092;
        padding-bottom: 15px;
        margin-bottom: 20px;
    }
    
    .header h1 {
        margin: 0;
        font-size: 18pt;
    }
    
    .header .subtitle {
        color: #666;
        font-size: 11pt;
        margin-top: 5px;
    }
    
    .header .meta {
        font-size: 9pt;
        color: #888;
        margin-top: 10px;
    }

    .summary-box {
        background-color: #f5f5f5;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }
    
    .summary-box h3 {
        margin: 0 0 10px 0;
        font-size: 12pt;
    }
    
    .summary-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
    }
    
    .summary-item {
        flex: 1;
        min-width: 150px;
    }
    
    .summary-label {
        font-weight: bold;
        font-size: 9pt;
        color: #666;
    }
    
    .summary-value {
        font-size: 14pt;
        font-weight: bold;
        color: #333;
    }
    
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 3px;
        font-size: 8pt;
        font-weight: bold;
    }
    
    .badge-success { background-color: #d4edda; color: #155724; }
    .badge-warning { background-color: #fff3cd; color: #856404; }
    .badge-danger { background-color: #f8d7da; color: #721c24; }
    .badge-info { background-color: #d1ecf1; color: #0c5460; }
    .badge-primary { background-color: #cce5ff; color: #004085; }
    
    .text-right { text-align: right; }
    .text-center { text-align: center; }
    
    .amount-positive { color: #28a745; }
    .amount-negative { color: #dc3545; }
    
    .footer {
        margin-top: 30px;
        padding-top: 15px;
        border-top: 1px solid #ddd;
        font-size: 8pt;
        color: #666;
        text-align: center;
    }
    
    .no-print { display: none; }
    """
    
    @classmethod
    def generate_pdf(cls, template_name, context, filename=None, request=None):
        """
        Génère un PDF à partir d'un template HTML.
        
        Args:
            template_name: Nom du template HTML
            context: Contexte pour le template
            filename: Nom du fichier PDF (optionnel)
            request: Requête HTTP (optionnel, pour les URLs absolues)
        
        Returns:
            HttpResponse avec le PDF
        """
        try:
            # Ajouter des données communes au contexte
            context['print_date'] = datetime.now()
            context['site_name'] = getattr(settings, 'SITE_NAME', 'EEBC')
            
            # Rendre le template HTML
            html_string = render_to_string(template_name, context, request=request)
            
            # Configuration des polices
            font_config = FontConfiguration()
            
            # Créer le PDF
            html = HTML(string=html_string, base_url=request.build_absolute_uri('/') if request else None)
            css = CSS(string=cls.BASE_CSS, font_config=font_config)
            
            # Générer le PDF en mémoire
            pdf_buffer = BytesIO()
            html.write_pdf(pdf_buffer, stylesheets=[css], font_config=font_config)
            pdf_buffer.seek(0)
            
            # Créer la réponse HTTP
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"document_{timestamp}.pdf"
            
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du PDF: {e}")
            raise

    @classmethod
    def generate_pdf_download(cls, template_name, context, filename=None, request=None):
        """
        Génère un PDF en téléchargement (attachment).
        """
        response = cls.generate_pdf(template_name, context, filename, request)
        # Changer pour forcer le téléchargement
        response['Content-Disposition'] = response['Content-Disposition'].replace('inline', 'attachment')
        return response


# Instance globale du service
pdf_service = PDFService()
