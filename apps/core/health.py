"""
Health checks pour le monitoring de l'application.
"""
import logging
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
import time

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Endpoint de health check complet.
    Vérifie tous les services critiques.
    """
    checks = {
        'timestamp': timezone.now().isoformat(),
        'status': 'healthy',
        'checks': {}
    }
    
    # Vérifier la base de données
    db_status = check_database()
    checks['checks']['database'] = db_status
    
    # Vérifier le cache
    cache_status = check_cache()
    checks['checks']['cache'] = cache_status
    
    # Vérifier les services externes (si configurés)
    if hasattr(settings, 'STRIPE_SECRET_KEY') and settings.STRIPE_SECRET_KEY:
        stripe_status = check_stripe()
        checks['checks']['stripe'] = stripe_status
    
    if hasattr(settings, 'TWILIO_ACCOUNT_SID') and settings.TWILIO_ACCOUNT_SID:
        twilio_status = check_twilio()
        checks['checks']['twilio'] = twilio_status
    
    # Vérifier l'espace disque
    disk_status = check_disk_space()
    checks['checks']['disk'] = disk_status
    
    # Déterminer le statut global
    all_healthy = all(
        check.get('status') == 'healthy' 
        for check in checks['checks'].values()
    )
    
    if not all_healthy:
        checks['status'] = 'unhealthy'
        status_code = 503
    else:
        status_code = 200
    
    return JsonResponse(checks, status=status_code)


def check_database():
    """Vérifie la connectivité à la base de données."""
    try:
        start_time = time.time()
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        response_time = (time.time() - start_time) * 1000  # en ms
        
        return {
            'status': 'healthy',
            'response_time_ms': round(response_time, 2),
            'message': 'Database connection successful'
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'message': 'Database connection failed'
        }


def check_cache():
    """Vérifie le fonctionnement du cache."""
    try:
        start_time = time.time()
        
        # Test d'écriture/lecture
        test_key = 'health_check_test'
        test_value = f'test_{int(time.time())}'
        
        cache.set(test_key, test_value, 60)
        retrieved_value = cache.get(test_key)
        
        if retrieved_value != test_value:
            raise Exception("Cache read/write mismatch")
        
        # Nettoyer
        cache.delete(test_key)
        
        response_time = (time.time() - start_time) * 1000  # en ms
        
        return {
            'status': 'healthy',
            'response_time_ms': round(response_time, 2),
            'message': 'Cache read/write successful'
        }
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'message': 'Cache operation failed'
        }


def check_stripe():
    """Vérifie la connectivité à Stripe."""
    try:
        import stripe
        from django.conf import settings
        
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        start_time = time.time()
        
        # Test simple : récupérer les informations du compte
        account = stripe.Account.retrieve()
        
        response_time = (time.time() - start_time) * 1000  # en ms
        
        return {
            'status': 'healthy',
            'response_time_ms': round(response_time, 2),
            'message': f'Stripe API accessible (Account: {account.id})'
        }
    except Exception as e:
        logger.error(f"Stripe health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'message': 'Stripe API connection failed'
        }


def check_twilio():
    """Vérifie la connectivité à Twilio."""
    try:
        from twilio.rest import Client
        from django.conf import settings
        
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        start_time = time.time()
        
        # Test simple : récupérer les informations du compte
        account = client.api.accounts(settings.TWILIO_ACCOUNT_SID).fetch()
        
        response_time = (time.time() - start_time) * 1000  # en ms
        
        return {
            'status': 'healthy',
            'response_time_ms': round(response_time, 2),
            'message': f'Twilio API accessible (Status: {account.status})'
        }
    except Exception as e:
        logger.error(f"Twilio health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'message': 'Twilio API connection failed'
        }


def check_disk_space():
    """Vérifie l'espace disque disponible."""
    try:
        import shutil
        
        # Vérifier l'espace disque du répertoire de l'application
        total, used, free = shutil.disk_usage('/')
        
        # Convertir en GB
        total_gb = total // (1024**3)
        used_gb = used // (1024**3)
        free_gb = free // (1024**3)
        
        usage_percent = (used / total) * 100
        
        # Seuil d'alerte à 85%
        if usage_percent > 85:
            status = 'unhealthy'
            message = f'Disk usage critical: {usage_percent:.1f}%'
        elif usage_percent > 75:
            status = 'warning'
            message = f'Disk usage high: {usage_percent:.1f}%'
        else:
            status = 'healthy'
            message = f'Disk usage normal: {usage_percent:.1f}%'
        
        return {
            'status': status,
            'usage_percent': round(usage_percent, 1),
            'total_gb': total_gb,
            'used_gb': used_gb,
            'free_gb': free_gb,
            'message': message
        }
    except Exception as e:
        logger.error(f"Disk space health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'message': 'Disk space check failed'
        }


def readiness_check(request):
    """
    Endpoint de readiness check.
    Vérifie si l'application est prête à recevoir du trafic.
    """
    checks = {
        'timestamp': timezone.now().isoformat(),
        'status': 'ready',
        'checks': {}
    }
    
    # Vérifications critiques pour la readiness
    db_status = check_database()
    checks['checks']['database'] = db_status
    
    # Vérifier que les migrations sont appliquées
    migration_status = check_migrations()
    checks['checks']['migrations'] = migration_status
    
    # Déterminer le statut global
    all_ready = all(
        check.get('status') == 'healthy' 
        for check in checks['checks'].values()
    )
    
    if not all_ready:
        checks['status'] = 'not_ready'
        status_code = 503
    else:
        status_code = 200
    
    return JsonResponse(checks, status=status_code)


def check_migrations():
    """Vérifie que toutes les migrations sont appliquées."""
    try:
        from django.core.management import execute_from_command_line
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connections
        
        executor = MigrationExecutor(connections['default'])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        if plan:
            return {
                'status': 'unhealthy',
                'message': f'{len(plan)} unapplied migrations found',
                'pending_migrations': len(plan)
            }
        else:
            return {
                'status': 'healthy',
                'message': 'All migrations applied',
                'pending_migrations': 0
            }
    except Exception as e:
        logger.error(f"Migration check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'message': 'Migration check failed'
        }


def liveness_check(request):
    """
    Endpoint de liveness check.
    Vérifie si l'application est vivante (basique).
    """
    return JsonResponse({
        'timestamp': timezone.now().isoformat(),
        'status': 'alive',
        'message': 'Application is running'
    })