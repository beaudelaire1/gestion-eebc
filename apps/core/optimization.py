"""
Utilitaires d'optimisation pour les requêtes BD et caching.
"""

from django.core.cache import cache
from django.views.decorators.cache import cache_page
from functools import wraps
from datetime import timedelta


def cache_result(timeout=300, key_prefix=None):
    """
    Décorateur pour cacher les résultats de fonctions.
    
    Usage:
        @cache_result(timeout=600, key_prefix='users_list')
        def get_users():
            return User.objects.all()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Générer une clé unique basée sur le nom de la fonction et les arguments
            cache_key = f"{key_prefix or func.__name__}:{args}:{kwargs}"
            cache_key = cache_key.replace(' ', '').replace("'", '')
            
            result = cache.get(cache_key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def invalidate_cache(*patterns):
    """
    Invalider le cache pour les patterns donnés.
    
    Usage:
        invalidate_cache('users_list', 'member_*')
    """
    for pattern in patterns:
        # Implémentation simple - peut être améliorée avec redis patterns
        cache.clear()


class CacheConfig:
    """Configuration des timeouts de cache par type."""
    
    # Cache court terme (1 minute)
    SHORT = 60
    
    # Cache moyen terme (5 minutes)
    MEDIUM = 300
    
    # Cache long terme (30 minutes)
    LONG = 1800
    
    # Cache très long terme (1 heure)
    VERY_LONG = 3600
    
    # Cache d'une journée
    DAY = 86400
    
    @staticmethod
    def get_members_timeout():
        """Timeout pour les listes de membres."""
        return CacheConfig.MEDIUM
    
    @staticmethod
    def get_events_timeout():
        """Timeout pour les événements."""
        return CacheConfig.MEDIUM
    
    @staticmethod
    def get_finance_timeout():
        """Timeout pour les données financières."""
        return CacheConfig.LONG
    
    @staticmethod
    def get_statistics_timeout():
        """Timeout pour les statistiques."""
        return CacheConfig.LONG


def optimize_queryset(queryset, select_related_fields=None, prefetch_related_fields=None):
    """
    Optimiser un queryset avec select_related et prefetch_related.
    
    Usage:
        queryset = Member.objects.all()
        queryset = optimize_queryset(
            queryset,
            select_related_fields=['user', 'site'],
            prefetch_related_fields=['life_events', 'visits_received']
        )
    """
    if select_related_fields:
        queryset = queryset.select_related(*select_related_fields)
    
    if prefetch_related_fields:
        queryset = queryset.prefetch_related(*prefetch_related_fields)
    
    return queryset


# Configuration des optimisations par modèle
OPTIMIZATION_CONFIGS = {
    'Member': {
        'select_related': ['user', 'site', 'family'],
        'prefetch_related': ['life_events', 'visits_received']
    },
    'Event': {
        'select_related': ['site', 'category'],
        'prefetch_related': ['registrations']
    },
    'FinancialTransaction': {
        'select_related': ['member', 'site', 'category'],
        'prefetch_related': ['proofs']
    },
    'DriverProfile': {
        'select_related': ['user'],
        'prefetch_related': ['transport_requests']
    },
    'Child': {
        'select_related': ['bible_class', 'assigned_driver'],
        'prefetch_related': ['attendances']
    },
    'User': {
        'select_related': [],
        'prefetch_related': ['groups', 'user_permissions']
    }
}


def get_optimized_queryset(model_name, queryset):
    """
    Obtenir un queryset optimisé selon la configuration.
    
    Usage:
        from apps.core.optimization import get_optimized_queryset
        members = Member.objects.all()
        members = get_optimized_queryset('Member', members)
    """
    config = OPTIMIZATION_CONFIGS.get(model_name, {})
    return optimize_queryset(
        queryset,
        select_related_fields=config.get('select_related'),
        prefetch_related_fields=config.get('prefetch_related')
    )


# Logging des requêtes en développement
def log_queries(func):
    """
    Décorateur pour logger les requêtes SQL en développement.
    """
    def wrapper(*args, **kwargs):
        from django.conf import settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        if settings.DEBUG:
            with CaptureQueriesContext(connection) as ctx:
                result = func(*args, **kwargs)
            
            if len(ctx.captured_queries) > 10:
                print(f"⚠️  {func.__name__} exécute {len(ctx.captured_queries)} requêtes !")
                for i, query in enumerate(ctx.captured_queries, 1):
                    print(f"   {i}. {query['sql'][:100]}...")
            
            return result
        else:
            return func(*args, **kwargs)
    
    return wrapper
