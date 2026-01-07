"""
URLs pour les health checks.
"""
from django.urls import path
from .health import health_check, readiness_check, liveness_check

urlpatterns = [
    path('', health_check, name='health_check'),
    path('ready/', readiness_check, name='readiness_check'),
    path('alive/', liveness_check, name='liveness_check'),
]