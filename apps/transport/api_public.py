"""API publique de suivi passager, accessible par token UUID."""
from datetime import timedelta
from uuid import UUID

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import TransportRequest


TRACKABLE_STATUSES = {
    TransportRequest.Status.CONFIRMED,
    TransportRequest.Status.EN_ROUTE,
    TransportRequest.Status.ARRIVING,
}
PUBLIC_API_RATE_LIMIT = 120
PUBLIC_PAGE_RATE_LIMIT = 30
RATE_LIMIT_WINDOW_SECONDS = 60


def _parse_tracking_token(tracking_token):
    try:
        return UUID(str(tracking_token))
    except (TypeError, ValueError):
        return None


def _client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _is_rate_limited(request, tracking_token, scope, limit):
    cache_key = (
        f"transport:public-tracking:{scope}:"
        f"{tracking_token}:{_client_ip(request)}"
    )
    if cache.add(cache_key, 1, RATE_LIMIT_WINDOW_SECONDS):
        return False
    try:
        return cache.incr(cache_key) > limit
    except ValueError:
        cache.set(cache_key, 1, RATE_LIMIT_WINDOW_SECONDS)
        return False


def _transport_request_for_token(tracking_token):
    parsed_token = _parse_tracking_token(tracking_token)
    if parsed_token is None:
        return None

    return TransportRequest.objects.select_related(
        'driver__user',
        'live_location',
    ).filter(tracking_token=parsed_token).first()


def _tracking_link_expired(transport_request):
    return transport_request.event_date < timezone.localdate() - timedelta(days=1)


def _can_track(transport_request):
    return transport_request.status in TRACKABLE_STATUSES


def _driver_phone(driver):
    if not driver or not hasattr(driver.user, 'profile'):
        return None
    return getattr(driver.user.profile, 'phone', None)


def _masked_phone(phone):
    if not phone:
        return None
    visible_digits = ''.join(char for char in phone if char.isdigit())[-2:]
    return f"••••••{visible_digits}" if visible_digits else None


@require_http_methods(["GET"])
def tracking_api_json(request, tracking_token):
    """
    API JSON publique pour le suivi passager.
    
    GET /transport/public/track/<token>/api/
    
    Réponse:
    {
        "request_id": 123,
        "status": "en_route",
        "requester_name": "Alice",
        "passengers_count": 2,
        "pickup_address": "15 rue Test",
        "can_track": true,
        "driver": {
            "name": "Jean Dupont",
            "phone": "+594....",
            "vehicle": {
                "type": "Minibus",
                "capacity": 8
            }
        },
        "position": {
            "latitude": 4.922,
            "longitude": -52.305,
            "accuracy_m": 10.5,
            "speed_kmh": 45.2,
            "recorded_at": "2026-05-06T16:46:00Z"
        },
        "eta_minutes": 5,
        "tracking_status": "active",
        "last_update": "2026-05-06T16:46:00Z"
    }
    """
    if _is_rate_limited(request, tracking_token, 'api', PUBLIC_API_RATE_LIMIT):
        return JsonResponse(
            {"error": "Trop de requêtes, veuillez réessayer dans une minute"},
            status=429,
        )

    transport_request = _transport_request_for_token(tracking_token)
    if transport_request is None or _tracking_link_expired(transport_request):
        return JsonResponse(
            {"error": "Lien de suivi invalide ou expiré"},
            status=404
        )

    can_track = _can_track(transport_request)
    live_location = getattr(transport_request, 'live_location', None)

    data = {
        "request_id": transport_request.pk,
        "status": transport_request.status,
        "requester_name": transport_request.requester_name,
        "passengers_count": transport_request.passengers_count,
        "pickup_address": transport_request.pickup_address,
        "can_track": can_track,
        "driver": None,
        "position": None,
        "eta_minutes": None,
        "tracking_status": "not_started",
        "last_update": None,
    }

    if transport_request.driver:
        data["driver"] = {
            "name": transport_request.driver.user.get_full_name(),
            "phone": _masked_phone(_driver_phone(transport_request.driver)),
            "vehicle": {
                "type": transport_request.driver.vehicle_type,
                "capacity": transport_request.driver.capacity,
                "model": transport_request.driver.vehicle_model or None,
            }
        }

    if live_location:
        live = live_location
        data["position"] = {
            "latitude": float(live.latitude),
            "longitude": float(live.longitude),
            "accuracy_m": float(live.accuracy_m) if live.accuracy_m else None,
            "speed_kmh": float(live.speed_kmh) if live.speed_kmh else None,
            "heading_deg": float(live.heading_deg) if live.heading_deg else None,
            "recorded_at": live.recorded_at.isoformat(),
        }
        data["last_update"] = live.updated_at.isoformat()
        data["tracking_status"] = "active" if live.is_active else "paused"

    if can_track and transport_request.status in [
        TransportRequest.Status.EN_ROUTE,
        TransportRequest.Status.ARRIVING,
    ] and live_location:
        if transport_request.status == TransportRequest.Status.ARRIVING:
            data["eta_minutes"] = "~2-5"
        else:
            data["eta_minutes"] = "~10-15"
    
    return JsonResponse(data)


@require_http_methods(["GET"])
def tracking_page_html(request, tracking_token):
    """
    Page HTML publique de suivi pour le passager.
    
    GET /transport/public/track/<token>/
    
    Affiche:
    - Carte avec position en temps réel (Leaflet)
    - Infos chauffeur
    - ETA
    - Adresse prise en charge
    - Statut trajet
    - Polling auto toutes les 5 secondes
    """
    if _is_rate_limited(request, tracking_token, 'page', PUBLIC_PAGE_RATE_LIMIT):
        return render(
            request,
            'transport/public_tracking_invalid.html',
            {'message': 'Trop de requêtes, veuillez réessayer dans une minute.'},
            status=429,
        )

    transport_request = _transport_request_for_token(tracking_token)
    if transport_request is None or _tracking_link_expired(transport_request):
        return render(
            request,
            'transport/public_tracking_invalid.html',
            {'message': "Désolé, ce lien de suivi n'est plus valide ou a expiré."},
            status=404,
        )

    initial_lat = 4.9
    initial_lng = -52.3
    zoom = 10

    if transport_request.pickup_latitude and transport_request.pickup_longitude:
        initial_lat = float(transport_request.pickup_latitude)
        initial_lng = float(transport_request.pickup_longitude)
        zoom = 13

    return render(
        request,
        'transport/public_tracking.html',
        {
            'transport_request': transport_request,
            'driver_phone_display': _masked_phone(_driver_phone(transport_request.driver)),
            'tracking_config': {
                'apiUrl': reverse('transport:public_track_api', args=[transport_request.tracking_token]),
                'initialLat': initial_lat,
                'initialLng': initial_lng,
                'zoom': zoom,
            },
        },
    )
