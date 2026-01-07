"""
URLs pour les health checks.
"""
from django.urls import path
from django.http import HttpResponse
from .health import health_check, readiness_check, liveness_check

def ping(request):
    """Simple ping - retourne OK sans vérification"""
    return HttpResponse("OK", content_type="text/plain")

urlpatterns = [
    path('', health_check, name='health_check'),
    path('ping/', ping, name='ping'),
    path('ready/', readiness_check, name='readiness_check'),
    path('alive/', liveness_check, name='liveness_check'),
]