"""
Utilitaire CloudFlare Turnstile pour validation CAPTCHA.

CloudFlare Turnstile est une alternative moderne à reCAPTCHA :
- Gratuit et illimité
- Meilleur UX (pas de puzzles complexes)
- Pas de tracking Google
- Plus rapide et moins intrusif

Documentation: https://developers.cloudflare.com/turnstile/

Configuration requise dans settings :
- TURNSTILE_SITE_KEY : Clé publique (front-end)
- TURNSTILE_SECRET_KEY : Clé secrète (back-end)
"""

import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def validate_turnstile(token: str, ip_address: str = None) -> tuple[bool, str | None]:
    """
    Valide un token CloudFlare Turnstile auprès de l'API.
    
    Args:
        token: Le token généré par le widget Turnstile côté client
        ip_address: IP de l'utilisateur (optionnel mais recommandé)
        
    Returns:
        tuple: (bool succès, str message d'erreur ou None)
        
    Exemple:
        >>> is_valid, error = validate_turnstile(request.POST.get('cf-turnstile-response'))
        >>> if not is_valid:
        >>>     messages.error(request, error)
    """
    # Si les clés ne sont pas configurées, mode passthrough en dev
    secret_key = getattr(settings, 'TURNSTILE_SECRET_KEY', '')
    
    if not secret_key:
        if settings.DEBUG:
            logger.info("TURNSTILE_SECRET_KEY non configurée, validation ignorée en mode DEBUG")
            return True, None
        else:
            logger.error("TURNSTILE_SECRET_KEY non configurée en production")
            return False, "Configuration de sécurité manquante."

    if not token:
        return False, "Token de sécurité manquant."

    try:
        data = {
            'secret': secret_key,
            'response': token
        }
        
        # Ajouter l'IP si fournie (recommandé)
        if ip_address:
            data['remoteip'] = ip_address
        
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data=data,
            timeout=5
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            logger.debug(f"Turnstile validation réussie pour IP {ip_address}")
            return True, None
        else:
            error_codes = result.get('error-codes', [])
            logger.warning(f"Turnstile validation échouée: {error_codes}")
            
            # Messages d'erreur plus explicites
            if 'timeout-or-duplicate' in error_codes:
                return False, "Token expiré ou déjà utilisé. Veuillez réessayer."
            elif 'invalid-input-response' in error_codes:
                return False, "Token invalide. Veuillez réessayer."
            elif 'invalid-input-secret' in error_codes:
                logger.error("TURNSTILE_SECRET_KEY invalide (configuration)")
                return False, "Erreur de configuration. Contactez l'administrateur."
            
            # En dev, mode laxiste
            if settings.DEBUG:
                logger.warning("DEBUG: Turnstile invalide mais accepté en mode dev")
                return True, None
            
            return False, "Vérification de sécurité échouée. Veuillez réessayer."
            
    except requests.Timeout:
        logger.error("Timeout lors de la validation Turnstile")
        # En dev, laisser passer
        if settings.DEBUG:
            logger.warning("DEBUG: Timeout Turnstile ignoré en mode dev")
            return True, None
        return False, "Délai de vérification dépassé. Veuillez réessayer."
        
    except requests.RequestException as e:
        logger.error(f"Erreur de connexion Turnstile: {e}")
        # En dev, laisser passer
        if settings.DEBUG:
            logger.warning("DEBUG: Erreur Turnstile ignorée en mode dev")
            return True, None
        return False, "Erreur lors de la vérification de sécurité."


def get_client_ip(request) -> str:
    """
    Récupère l'IP réelle du client (gère les proxies/CDNs).
    
    Args:
        request: Objet HttpRequest Django
        
    Returns:
        str: Adresse IP du client
    """
    # Vérifier les headers de proxy (Cloudflare, Render, etc.)
    ip = request.META.get('HTTP_CF_CONNECTING_IP')  # CloudFlare
    if not ip:
        ip = request.META.get('HTTP_X_FORWARDED_FOR')  # Proxy standard
        if ip:
            # Prendre la première IP si plusieurs
            ip = ip.split(',')[0].strip()
    if not ip:
        ip = request.META.get('REMOTE_ADDR')  # IP directe
    
    return ip or '0.0.0.0'


def validate_turnstile_with_ip(request) -> tuple[bool, str | None]:
    """
    Valide Turnstile en récupérant automatiquement le token et l'IP depuis la requête.
    
    Args:
        request: Objet HttpRequest Django
        
    Returns:
        tuple: (bool succès, str message d'erreur ou None)
        
    Exemple:
        >>> from apps.core.utils.turnstile import validate_turnstile_with_ip
        >>> is_valid, error = validate_turnstile_with_ip(request)
        >>> if not is_valid:
        >>>     return render(request, 'error.html', {'error': error})
    """
    token = request.POST.get('cf-turnstile-response')
    ip_address = get_client_ip(request)
    
    return validate_turnstile(token, ip_address)
