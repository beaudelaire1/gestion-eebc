"""
Health check endpoints for monitoring.

Provides system health status: DB, cache, Celery, and overall status.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import connections
from django.db.utils import OperationalError
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def health_check(request):
    """
    GET /health/
    
    Returns system health status (JSON).
    
    Response:
    {
      "status": "ok" | "degraded" | "critical",
      "timestamp": "2026-04-21T03:00:00Z",
      "db": "ok" | "error",
      "cache": "ok" | "error",
      "celery": {
        "status": "ok" | "error",
        "workers": <count>
      },
      "errors": [...]  # Only if status != "ok"
    }
    """
    errors = []
    
    # Check database
    db_status = _check_database()
    if db_status['status'] != 'ok':
        errors.append(f"Database: {db_status['error']}")
    
    # Check cache (Redis)
    cache_status = _check_cache()
    if cache_status['status'] != 'ok':
        errors.append(f"Cache: {cache_status['error']}")
    
    # Check Celery
    celery_status = _check_celery()
    if celery_status['status'] != 'ok':
        errors.append(f"Celery: {celery_status['error']}")
    
    # Determine overall status
    if not errors:
        overall_status = 'ok'
        http_status = 200
    elif len(errors) == 1 and cache_status['status'] != 'ok':
        # Only cache down is degraded (can still operate)
        overall_status = 'degraded'
        http_status = 200
    else:
        overall_status = 'critical'
        http_status = 503
    
    response = {
        'status': overall_status,
        'timestamp': timezone.now().isoformat(),
        'db': db_status['status'],
        'cache': cache_status['status'],
        'celery': {
            'status': celery_status['status'],
            'workers': celery_status.get('workers', 0),
        },
    }
    
    if errors:
        response['errors'] = errors
    
    return JsonResponse(response, status=http_status)


def _check_database():
    """Check PostgreSQL connection."""
    try:
        # Attempt a simple query
        connection = connections['default']
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        
        return {'status': 'ok'}
    except OperationalError as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'status': 'error',
            'error': str(e)[:100]  # Limit error message
        }
    except Exception as e:
        logger.error(f"Unexpected database check error: {e}")
        return {
            'status': 'error',
            'error': 'Unknown database error'
        }


def _check_cache():
    """Check Redis/cache connection."""
    try:
        # Test cache set/get
        test_key = '__health_check__'
        test_value = timezone.now().isoformat()
        
        cache.set(test_key, test_value, 10)
        retrieved = cache.get(test_key)
        cache.delete(test_key)
        
        if retrieved == test_value:
            return {'status': 'ok'}
        else:
            return {
                'status': 'error',
                'error': 'Cache get/set mismatch'
            }
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            'status': 'error',
            'error': str(e)[:100]
        }


def _check_celery():
    """Check Celery broker and active workers."""
    try:
        from celery import Celery
        from gestion_eebc import celery_app
        
        # Inspect active tasks / workers
        inspect = celery_app.control.inspect()
        
        if inspect is None:
            return {
                'status': 'error',
                'error': 'Celery inspect unavailable (broker unreachable?)',
                'workers': 0
            }
        
        # Get active workers
        try:
            active_workers = inspect.active()
            if active_workers is None:
                return {
                    'status': 'warning',
                    'error': 'No active workers detected',
                    'workers': 0
                }
            
            worker_count = len(active_workers)
            return {
                'status': 'ok',
                'workers': worker_count
            }
        except Exception as e:
            logger.warning(f"Celery worker check failed: {e}")
            return {
                'status': 'warning',
                'error': f'Worker check failed: {str(e)[:50]}',
                'workers': 0
            }
    
    except ImportError:
        # Celery not configured
        return {
            'status': 'warning',
            'error': 'Celery not configured',
            'workers': 0
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {
            'status': 'error',
            'error': str(e)[:100],
            'workers': 0
        }


# Lightweight version (no Celery check, faster)
@require_http_methods(["GET"])
def health_check_lite(request):
    """
    GET /health/lite/
    
    Fast health check (DB + cache only, no Celery).
    """
    db_status = _check_database()
    cache_status = _check_cache()
    
    errors = []
    if db_status['status'] != 'ok':
        errors.append('db')
    if cache_status['status'] != 'ok':
        errors.append('cache')
    
    response = {
        'status': 'ok' if not errors else 'error',
        'timestamp': timezone.now().isoformat(),
    }
    
    if errors:
        response['failed_checks'] = errors
    
    http_status = 200 if not errors else 503
    return JsonResponse(response, status=http_status)
