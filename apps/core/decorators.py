"""
Décorateurs personnalisés pour la gestion d'erreurs et l'optimisation.
"""
import functools
import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


def handle_external_service_errors(func):
    """
    Décorateur pour gérer les erreurs des services externes.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log spécifique selon le type d'erreur
            if 'stripe' in str(e).lower():
                logger.error(f"Stripe error in {func.__name__}: {e}")
                return {'success': False, 'error': 'Service de paiement temporairement indisponible'}
            elif 'twilio' in str(e).lower():
                logger.error(f"Twilio error in {func.__name__}: {e}")
                return {'success': False, 'error': 'Service SMS temporairement indisponible'}
            else:
                logger.exception(f"Unexpected error in {func.__name__}")
                return {'success': False, 'error': 'Service temporairement indisponible'}
    return wrapper


def cache_result(timeout=300, key_prefix=''):
    """
    Décorateur pour mettre en cache le résultat d'une fonction.
    
    Args:
        timeout: Durée du cache en secondes (défaut: 5 minutes)
        key_prefix: Préfixe pour la clé de cache
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Générer une clé de cache basée sur les arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Vérifier le cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Calculer et mettre en cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def require_ajax(func):
    """
    Décorateur pour s'assurer qu'une vue n'est accessible qu'en AJAX.
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if not (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                request.headers.get('HX-Request')):
            return JsonResponse({'error': 'Cette vue nécessite une requête AJAX'}, status=400)
        return func(request, *args, **kwargs)
    return wrapper


def rate_limit_user(requests_per_minute=60):
    """
    Décorateur pour limiter le nombre de requêtes par utilisateur.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return func(request, *args, **kwargs)
            
            # Clé de cache basée sur l'utilisateur et la vue
            cache_key = f"rate_limit:{request.user.id}:{func.__name__}"
            
            # Compter les requêtes
            current_requests = cache.get(cache_key, 0)
            if current_requests >= requests_per_minute:
                return JsonResponse({
                    'error': 'Trop de requêtes. Veuillez patienter.'
                }, status=429)
            
            # Incrémenter le compteur
            cache.set(cache_key, current_requests + 1, 60)  # 1 minute
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def log_performance(func):
    """
    Décorateur pour logger les performances d'une fonction.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        duration = time.time() - start_time
        if duration > 1.0:  # Log si > 1 seconde
            logger.warning(f"Slow function {func.__name__}: {duration:.2f}s")
        
        return result
    return wrapper


def validate_json_request(required_fields=None):
    """
    Décorateur pour valider les requêtes JSON.
    
    Args:
        required_fields: Liste des champs requis dans le JSON
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            import json
            
            if request.content_type != 'application/json':
                return JsonResponse({'error': 'Content-Type doit être application/json'}, status=400)
            
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'JSON invalide'}, status=400)
            
            # Vérifier les champs requis
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return JsonResponse({
                        'error': f'Champs manquants: {", ".join(missing_fields)}'
                    }, status=400)
            
            # Ajouter les données à la requête
            request.json = data
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def permission_required_ajax(permission):
    """
    Décorateur pour vérifier les permissions en AJAX.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.has_perm(permission):
                return JsonResponse({'error': 'Permission insuffisante'}, status=403)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator