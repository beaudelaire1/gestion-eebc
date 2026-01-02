"""
Service OCR pour l'extraction de données des reçus.

Utilise Tesseract OCR pour extraire :
- Montants
- Dates
- Texte brut

Note: Tesseract doit être installé sur le système.
Sur Windows: https://github.com/UB-Mannheim/tesseract/wiki
Sur Linux: sudo apt install tesseract-ocr tesseract-ocr-fra
"""

import re
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.utils import timezone

logger = logging.getLogger(__name__)


class OCRService:
    """Service pour l'extraction OCR des reçus."""
    
    def __init__(self):
        self.tesseract_available = False
        self._check_tesseract()
    
    def _check_tesseract(self):
        """Vérifie si Tesseract est disponible."""
        try:
            import pytesseract
            # Tester si Tesseract est installé
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            logger.info("Tesseract OCR is available")
        except Exception as e:
            logger.warning(f"Tesseract OCR not available: {e}")
            self.tesseract_available = False
    
    def process_receipt(self, receipt_proof):
        """
        Traite une image de reçu avec OCR.
        
        Args:
            receipt_proof: Instance de ReceiptProof
        
        Returns:
            dict: Données extraites ou None si échec
        """
        if not self.tesseract_available:
            receipt_proof.ocr_status = 'echec'
            receipt_proof.save()
            return {'error': 'Tesseract OCR not available'}
        
        try:
            import pytesseract
            from PIL import Image
            
            receipt_proof.ocr_status = 'en_cours'
            receipt_proof.save()
            
            # Ouvrir l'image
            img = Image.open(receipt_proof.image.path)
            
            # Prétraitement de l'image pour améliorer l'OCR
            img = self._preprocess_image(img)
            
            # Extraction du texte
            text = pytesseract.image_to_string(img, lang='fra')
            
            # Extraction des données
            amount = self._extract_amount(text)
            date = self._extract_date(text)
            
            # Calcul de la confiance (basé sur la présence de données)
            confidence = self._calculate_confidence(text, amount, date)
            
            # Mise à jour du modèle
            receipt_proof.ocr_raw_text = text
            receipt_proof.ocr_extracted_amount = amount
            receipt_proof.ocr_extracted_date = date
            receipt_proof.ocr_confidence = confidence
            receipt_proof.ocr_status = 'termine'
            receipt_proof.ocr_processed_at = timezone.now()
            receipt_proof.save()
            
            logger.info(f"OCR completed for receipt {receipt_proof.id}: amount={amount}, date={date}")
            
            return {
                'text': text,
                'amount': amount,
                'date': date,
                'confidence': confidence,
            }
        
        except Exception as e:
            logger.error(f"OCR failed for receipt {receipt_proof.id}: {e}")
            receipt_proof.ocr_status = 'echec'
            receipt_proof.save()
            return {'error': str(e)}
    
    def _preprocess_image(self, img):
        """Prétraite l'image pour améliorer l'OCR."""
        try:
            from PIL import ImageEnhance, ImageFilter
            
            # Convertir en niveaux de gris
            if img.mode != 'L':
                img = img.convert('L')
            
            # Augmenter le contraste
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # Augmenter la netteté
            img = img.filter(ImageFilter.SHARPEN)
            
            return img
        except Exception:
            return img
    
    def _extract_amount(self, text):
        """Extrait le montant du texte."""
        # Patterns pour les montants en euros
        patterns = [
            r'(?:total|montant|somme|ttc|net)[:\s]*(\d+[.,]\d{2})\s*(?:€|eur|euros?)?',
            r'(\d+[.,]\d{2})\s*(?:€|eur|euros?)',
            r'(?:€|eur|euros?)\s*(\d+[.,]\d{2})',
            r'(\d{1,3}(?:\s?\d{3})*[.,]\d{2})',
        ]
        
        amounts = []
        
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                try:
                    # Normaliser le format
                    amount_str = match.replace(',', '.').replace(' ', '')
                    amount = Decimal(amount_str)
                    if 0 < amount < 100000:  # Filtrer les valeurs aberrantes
                        amounts.append(amount)
                except (InvalidOperation, ValueError):
                    continue
        
        if amounts:
            # Retourner le montant le plus élevé (souvent le total)
            return max(amounts)
        
        return None
    
    def _extract_date(self, text):
        """Extrait la date du texte."""
        # Patterns pour les dates françaises
        patterns = [
            r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})',  # JJ/MM/AAAA
            r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2})',  # JJ/MM/AA
            r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})',
        ]
        
        months_fr = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
            'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
            'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
        }
        
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                try:
                    if len(match) == 3:
                        if match[1] in months_fr:
                            # Format: JJ mois AAAA
                            day = int(match[0])
                            month = months_fr[match[1]]
                            year = int(match[2])
                        else:
                            # Format: JJ/MM/AAAA ou JJ/MM/AA
                            day = int(match[0])
                            month = int(match[1])
                            year = int(match[2])
                            if year < 100:
                                year += 2000
                        
                        if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2100:
                            return datetime(year, month, day).date()
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _calculate_confidence(self, text, amount, date):
        """Calcule un score de confiance pour l'extraction."""
        score = 0.0
        
        # Texte non vide
        if text and len(text) > 50:
            score += 0.3
        
        # Montant trouvé
        if amount:
            score += 0.35
        
        # Date trouvée
        if date:
            score += 0.35
        
        return round(score * 100, 1)


# Instance singleton
ocr_service = OCRService()


def process_receipt_ocr(receipt_proof_id):
    """
    Fonction utilitaire pour traiter un reçu par ID.
    Peut être appelée comme tâche Celery.
    """
    from .models import ReceiptProof
    
    try:
        receipt = ReceiptProof.objects.get(id=receipt_proof_id)
        return ocr_service.process_receipt(receipt)
    except ReceiptProof.DoesNotExist:
        return {'error': 'Receipt not found'}
