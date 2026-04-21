"""
URL patterns for health checks.

Endpoints:
- GET /health/ → Full system health (DB, cache, Celery)
- GET /health/lite/ → Fast check (DB, cache only)
"""
from django.urls import path
from .health_views import health_check, health_check_lite

app_name = 'core_health'

urlpatterns = [
    path('', health_check, name='health_check'),
    path('lite/', health_check_lite, name='health_check_lite'),
]
