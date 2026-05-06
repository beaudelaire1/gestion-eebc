"""
API Publique pour le suivi tracking passager (sans authentification).
Accessible via token UUID unique par demande.
"""
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json

from .models import TransportRequest, DriverLiveLocation


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
    try:
        transport_request = TransportRequest.objects.select_related(
            'driver__user',
            'live_location'
        ).get(tracking_token=tracking_token)
    except TransportRequest.DoesNotExist:
        return JsonResponse(
            {"error": "Lien de suivi invalide ou expiré"},
            status=404
        )
    
    # Vérifier si le suivi est disponible
    can_track = transport_request.status not in [
        TransportRequest.Status.PENDING,
        TransportRequest.Status.COMPLETED,
        TransportRequest.Status.CANCELLED,
    ]
    
    # Construire la réponse
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
    
    # Ajouter infos chauffeur si assigné
    if transport_request.driver:
        data["driver"] = {
            "name": transport_request.driver.user.get_full_name(),
            "phone": getattr(
                transport_request.driver.user.profile,
                'phone',
                None
            ) if hasattr(transport_request.driver.user, 'profile') else None,
            "vehicle": {
                "type": transport_request.driver.vehicle_type,
                "capacity": transport_request.driver.capacity,
                "model": transport_request.driver.vehicle_model or None,
            }
        }
    
    # Ajouter position si disponible
    if hasattr(transport_request, 'live_location') and transport_request.live_location:
        live = transport_request.live_location
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
    
    # Ajouter ETA si applicable
    if can_track and transport_request.status in [
        TransportRequest.Status.EN_ROUTE,
        TransportRequest.Status.ARRIVING,
    ]:
        # TODO: Calculer ETA basé sur distance + vitesse moyenne
        # Pour maintenant, afficher position_update + message
        if transport_request.live_location:
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
    try:
        transport_request = TransportRequest.objects.select_related(
            'driver__user',
            'live_location'
        ).get(tracking_token=tracking_token)
    except TransportRequest.DoesNotExist:
        return HttpResponse("""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Lien expiré - EEBC Transport</title>
            <style>
                body { font-family: Poppins, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                h1 { color: #d32f2f; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>❌ Lien expiré</h1>
                <p>Désolé, ce lien de suivi n'est plus valide ou a expiré.</p>
                <p>Si vous avez besoin d'aide, contactez EEBC Transport.</p>
            </div>
        </body>
        </html>
        """, status=404, content_type='text/html')
    
    # Vérifier disponibilité suivi
    can_track = transport_request.status not in [
        TransportRequest.Status.PENDING,
        TransportRequest.Status.COMPLETED,
        TransportRequest.Status.CANCELLED,
    ]
    
    # Déterminer position initiale sur carte
    initial_lat = 4.9
    initial_lng = -52.3
    zoom = 10
    
    if transport_request.pickup_latitude and transport_request.pickup_longitude:
        initial_lat = float(transport_request.pickup_latitude)
        initial_lng = float(transport_request.pickup_longitude)
        zoom = 13
    
    driver_info = ""
    if transport_request.driver:
        driver_name = transport_request.driver.user.get_full_name()
        driver_phone = getattr(
            transport_request.driver.user.profile,
            'phone',
            'N/A'
        ) if hasattr(transport_request.driver.user, 'profile') else 'N/A'
        driver_vehicle = transport_request.driver.vehicle_type
        driver_info = f"""
        <div class="driver-info">
            <h3>👤 Votre chauffeur</h3>
            <p><strong>{driver_name}</strong></p>
            <p>Véhicule: {driver_vehicle}</p>
            <p>Tél: <a href="tel:{driver_phone}">{driver_phone}</a></p>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Suivi trajet - EEBC Transport</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body {{
                font-family: 'Poppins', sans-serif;
                background: linear-gradient(135deg, #0a0e27 0%, #0d1535 100%);
                min-height: 100vh;
                color: #fff;
                padding: 20px;
            }}
            .tracking-container {{
                max-width: 700px;
                margin: 0 auto;
            }}
            .card {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 15px;
                margin-bottom: 20px;
            }}
            #map {{
                height: 400px;
                border-radius: 12px;
                margin-bottom: 20px;
                border: 1px solid rgba(255,255,255,0.2);
            }}
            .status-badge {{
                padding: 8px 16px;
                border-radius: 50px;
                font-weight: 600;
                font-size: 14px;
                display: inline-block;
                margin-bottom: 15px;
            }}
            .status-badge.pending {{
                background: rgba(255, 152, 0, 0.2);
                color: #FFB74D;
            }}
            .status-badge.confirmed {{
                background: rgba(33, 150, 243, 0.2);
                color: #64B5F6;
            }}
            .status-badge.en_route {{
                background: rgba(76, 175, 80, 0.2);
                color: #81C784;
            }}
            .status-badge.arriving {{
                background: rgba(255, 193, 7, 0.2);
                color: #FFD54F;
            }}
            .status-badge.completed {{
                background: rgba(76, 175, 80, 0.2);
                color: #81C784;
            }}
            .info-row {{
                display: flex;
                justify-content: space-between;
                padding: 12px 0;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }}
            .info-row:last-child {{
                border-bottom: none;
            }}
            .info-label {{
                color: rgba(255,255,255,0.6);
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .info-value {{
                font-weight: 600;
                font-size: 14px;
            }}
            .driver-info {{
                background: rgba(255,165,0,0.1);
                border: 1px solid rgba(255,165,0,0.3);
                padding: 15px;
                border-radius: 10px;
                margin-top: 15px;
            }}
            .driver-info h3 {{
                font-size: 16px;
                margin-bottom: 10px;
                color: #FFB74D;
            }}
            .driver-info p {{
                margin: 6px 0;
                font-size: 14px;
            }}
            .driver-info a {{
                color: #64B5F6;
                text-decoration: none;
            }}
            .spinner {{
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid rgba(255,255,255,0.3);
                border-radius: 50%;
                border-top-color: #0A36FF;
                animation: spin 0.8s linear infinite;
            }}
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
            .updated-at {{
                font-size: 12px;
                color: rgba(255,255,255,0.5);
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="tracking-container">
            <div class="mb-4">
                <h2 style="margin-bottom: 10px;">🚗 Suivi de votre trajet</h2>
                <p style="color: rgba(255,255,255,0.7);">Suivez votre chauffeur en temps réel</p>
            </div>
            
            <div class="card p-4">
                <!-- Statut Badge -->
                <div id="status-container">
                    <span class="status-badge pending">
                        <i class="bi bi-clock spinner"></i>
                        Chargement...
                    </span>
                </div>
                
                <!-- Carte -->
                <div id="map"></div>
                
                <!-- Infos trajet -->
                <div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px;">
                    <div class="info-row">
                        <span class="info-label">📍 Lieu de prise en charge</span>
                    </div>
                    <p style="font-size: 14px; line-height: 1.5;">{transport_request.pickup_address}</p>
                    
                    <div class="info-row" style="margin-top: 15px;">
                        <span class="info-label">👥 Passagers</span>
                        <span class="info-value">{transport_request.passengers_count}</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="info-label">⏱️ ETA</span>
                        <span class="info-value" id="eta">--</span>
                    </div>
                </div>
                
                {driver_info}
                
                <div class="updated-at">
                    Dernière mise à jour: <span id="last-update">--</span>
                </div>
            </div>
        </div>
        
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
        const TRACKING_TOKEN = '{tracking_token}';
        const API_URL = `/transport/public/track/${{TRACKING_TOKEN}}/api/`;
        let map, driverMarker;
        
        // Initialiser la carte
        function initMap() {{
            map = L.map('map').setView([{initial_lat}, {initial_lng}], {zoom});
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap',
                maxZoom: 19,
            }}).addTo(map);
        }}
        
        // Mettre à jour le suivi
        async function updateTracking() {{
            try {{
                const response = await fetch(API_URL);
                if (!response.ok) {{
                    console.error('API error:', response.status);
                    return;
                }}
                
                const data = await response.json();
                
                // Statut
                const statusBadge = document.getElementById('status-container');
                const statusText = {{
                    'pending': '⏳ En attente',
                    'confirmed': '✅ Confirmé',
                    'en_route': '🚗 En route',
                    'arriving': '🔔 Arrive bientôt',
                    'completed': '✅ Effectué',
                    'cancelled': '❌ Annulé',
                }}[data.status] || 'Chargement...';
                
                statusBadge.innerHTML = `<span class="status-badge ${{data.status}}">${{statusText}}</span>`;
                
                // ETA
                if (data.eta_minutes !== null) {{
                    const etaText = typeof data.eta_minutes === 'string' ? 
                        data.eta_minutes + ' min' : 
                        data.eta_minutes + ' min';
                    document.getElementById('eta').textContent = etaText;
                }} else {{
                    document.getElementById('eta').textContent = 'Calcul...';
                }}
                
                // Position sur carte
                if (data.position && data.can_track) {{
                    const lat = data.position.latitude;
                    const lng = data.position.longitude;
                    
                    if (!driverMarker) {{
                        driverMarker = L.circleMarker([lat, lng], {{
                            radius: 8,
                            fillColor: '#0A36FF',
                            color: '#fff',
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.8
                        }}).addTo(map);
                        map.setView([lat, lng], 15);
                    }} else {{
                        driverMarker.setLatLng([lat, lng]);
                    }}
                }}
                
                // Mise à jour
                const lastUpdate = new Date(data.last_update || data.position?.recorded_at);
                const now = new Date();
                const diff = Math.floor((now - lastUpdate) / 1000);
                const timeStr = diff < 60 ? 'À l\'instant' : 
                                 diff < 3600 ? Math.floor(diff / 60) + ' min ago' :
                                 lastUpdate.toLocaleTimeString('fr-FR');
                document.getElementById('last-update').textContent = timeStr;
                
            }} catch (error) {{
                console.error('Tracking error:', error);
            }}
        }}
        
        // Initialiser et mettre à jour
        initMap();
        updateTracking();
        setInterval(updateTracking, 5000);  // Mise à jour toutes les 5 secondes
        </script>
    </body>
    </html>
    """
    
    return HttpResponse(html, content_type='text/html')
