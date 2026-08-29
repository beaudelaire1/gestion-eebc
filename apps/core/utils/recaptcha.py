import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def validate_recaptcha(token):
    """
    Valide un token reCAPTCHA v3 auprès de l'API Google.
    
    Args:
        token (str): Le token généré par le frontend reCAPTCHA.
        
    Returns:
        tuple: (bool, str) - (Succès, Message d'erreur éventuel)
    """
    # Si les clés ne sont pas configurées (ex: dev), on laisse passer
    if not settings.RECAPTCHA_PRIVATE_KEY:
        if settings.DEBUG:
            return True, None
        else:
            logger.error("RECAPTCHA_PRIVATE_KEY non configurée en production")
            return False, "Configuration de sécurité manquante."

    if not token:
        return False, "Token de sécurité manquant."

    try:
        data = {
            'secret': settings.RECAPTCHA_PRIVATE_KEY,
            'response': token
        }
        
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify', 
            data=data,
            timeout=5
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            score = result.get('score', 0.0)
            required_score = getattr(settings, 'RECAPTCHA_REQUIRED_SCORE', 0.5)
            
            if score >= required_score:
                return True, None
            else:
                if settings.DEBUG:
                     logger.warning(f"DEBUG: ReCAPTCHA score trop bas ({score}) mais accepté en dev.")
                     return True, None
                logger.warning(f"ReCAPTCHA score trop bas: {score}")
                return False, "Vérification de sécurité échouée (score faible)."
        else:
            errors = result.get('error-codes', [])
            logger.warning(f"ReCAPTCHA invalide: {errors}")
            
            if settings.DEBUG:
                logger.warning("DEBUG: ReCAPTCHA invalide mais accepté en dev (problème config probable).")
                return True, None
                
            return False, "Vérification de sécurité échouée."
            
    except requests.RequestException as e:
        logger.error(f"Erreur de connexion ReCAPTCHA: {e}")
        if settings.DEBUG:
            return True, None
        return False, "Erreur lors de la vérification de sécurité."
