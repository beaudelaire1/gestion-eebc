"""
Vues admin personnalisées pour les membres.
Inclut une carte interactive des membres par quartier/famille.
"""
import random
import math
import hashlib

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Q

from .models import Member
from .geocoding import geocode_address
from apps.core.models import Site, Neighborhood, Family, City
from apps.core.permissions import role_required, has_role


# =============================================================================
# GPS OBFUSCATION UTILITIES
# =============================================================================

def obfuscate_coordinates(lat, lng, min_offset_meters=50, max_offset_meters=100):
    """
    Ajoute un décalage aléatoire aux coordonnées GPS pour protéger la vie privée.
    
    Args:
        lat: Latitude originale
        lng: Longitude originale
        min_offset_meters: Décalage minimum en mètres (défaut: 50)
        max_offset_meters: Décalage maximum en mètres (défaut: 100)
    
    Returns:
        tuple: (latitude_obfusquée, longitude_obfusquée)
    
    Notes:
        - Le décalage est appliqué dans une direction aléatoire
        - La distance est aléatoire entre min_offset_meters et max_offset_meters
        - Utilise la formule de conversion degrés/mètres approximative
        - Gère les cas limites aux pôles (latitude ±90°)
    """
    # Conversion approximative: 1 degré de latitude ≈ 111,320 mètres
    # 1 degré de longitude ≈ 111,320 * cos(latitude) mètres
    METERS_PER_DEGREE_LAT = 111320
    
    # Générer une distance aléatoire entre min et max
    distance_meters = random.uniform(min_offset_meters, max_offset_meters)
    
    # Générer un angle aléatoire (0 à 2π)
    angle = random.uniform(0, 2 * math.pi)
    
    # Calculer le décalage en degrés
    lat_offset = (distance_meters * math.cos(angle)) / METERS_PER_DEGREE_LAT
    
    # Ajuster pour la longitude (dépend de la latitude)
    # Limiter la latitude à ±89.9° pour éviter la division par zéro aux pôles
    clamped_lat = max(-89.9, min(89.9, lat))
    meters_per_degree_lng = METERS_PER_DEGREE_LAT * math.cos(math.radians(clamped_lat))
    
    if meters_per_degree_lng > 0.01:  # Éviter la division par des valeurs très petites
        lng_offset = (distance_meters * math.sin(angle)) / meters_per_degree_lng
    else:
        # Aux pôles, le décalage en longitude n'a pas de sens, on l'ignore
        lng_offset = 0
    
    return (lat + lat_offset, lng + lng_offset)


def should_obfuscate_for_user(user):
    """
    Détermine si les coordonnées doivent être obfusquées pour un utilisateur.
    
    Args:
        user: L'utilisateur faisant la requête
    
    Returns:
        bool: True si les coordonnées doivent être obfusquées, False sinon
    
    Notes:
        - Les admins et superusers voient les coordonnées exactes
        - Tous les autres utilisateurs voient des coordonnées obfusquées
    """
    if not user or not user.is_authenticated:
        return True
    
    # Les superusers voient les coordonnées exactes
    if user.is_superuser:
        return False
    
    # Les admins voient les coordonnées exactes
    if user.has_role('admin'):
        return False
    
    # Tous les autres utilisateurs voient des coordonnées obfusquées
    return True


@login_required
@role_required('admin', 'secretariat')
def members_map_view(request):
    """Vue carte des membres (accessible aux admin et secretariat uniquement)."""
    
    # Filtres
    site_id = request.GET.get('site')
    neighborhood_id = request.GET.get('neighborhood')
    status = request.GET.get('status')
    
    # Sites pour le filtre
    sites = Site.objects.filter(is_active=True)
    neighborhoods = Neighborhood.objects.filter(is_active=True).select_related('city')
    
    context = {
        'title': 'Carte des membres',
        'sites': sites,
        'neighborhoods': neighborhoods,
        'selected_site': site_id,
        'selected_neighborhood': neighborhood_id,
        'selected_status': status,
        'status_choices': Member.Status.choices if hasattr(Member, 'Status') else [],
    }
    
    # Utiliser le template admin ou app selon le chemin
    if '/admin/' in request.path:
        return render(request, 'admin/members/members_map.html', context)
    return render(request, 'members/members_map.html', context)


@login_required
@role_required('admin', 'secretariat')
def members_map_data(request):
    """API JSON pour les données de la carte avec géocodage."""
    
    # Filtres
    site_id = request.GET.get('site')
    status = request.GET.get('status')
    city_filter = request.GET.get('city')
    
    # Déterminer si les coordonnées doivent être obfusquées
    obfuscate = should_obfuscate_for_user(request.user)
    
    # Données des sites (églises) - pas d'obfuscation pour les sites publics
    sites_data = []
    sites_qs = Site.objects.filter(
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    for site in sites_qs:
        member_count = Member.objects.filter(site=site).count()
        sites_data.append({
            'type': 'site',
            'id': site.id,
            'name': site.name,
            'lat': float(site.latitude),
            'lng': float(site.longitude),
            'address': site.address,
            'city': site.city,
            'member_count': member_count,
        })
    
    # Données des membres avec adresse
    members_data = []
    members_qs = Member.objects.filter(
        (Q(address__isnull=False) & ~Q(address='')) |
        (Q(family__address__isnull=False) & ~Q(family__address='')) |
        (Q(family__latitude__isnull=False) & Q(family__longitude__isnull=False))
    ).select_related('site', 'family')
    
    if site_id:
        members_qs = members_qs.filter(site_id=site_id)
    if status:
        members_qs = members_qs.filter(status=status)
    if city_filter:
        members_qs = members_qs.filter(
            Q(city__icontains=city_filter) |
            Q(family__city__icontains=city_filter) |
            Q(site__city__icontains=city_filter)
        )
    
    # Coordonnées fallback par ville (évite de perdre des marqueurs si le géocodage échoue)
    city_coords = {
        c.name.lower(): (float(c.latitude), float(c.longitude))
        for c in City.objects.filter(latitude__isnull=False, longitude__isnull=False)
    }

    # Cache pour éviter de géocoder plusieurs fois la même adresse
    geocode_cache = {}

    def deterministic_offset_coords(base_lat, base_lng, seed_value, min_offset_meters=80, max_offset_meters=220):
        seed = hashlib.sha256(str(seed_value).encode('utf-8')).hexdigest()
        angle_raw = int(seed[:8], 16)
        dist_raw = int(seed[8:16], 16)

        angle = (angle_raw / 0xFFFFFFFF) * 2 * math.pi
        distance_meters = min_offset_meters + ((dist_raw / 0xFFFFFFFF) * (max_offset_meters - min_offset_meters))

        meters_per_degree_lat = 111320
        lat_offset = (distance_meters * math.cos(angle)) / meters_per_degree_lat

        clamped_lat = max(-89.9, min(89.9, base_lat))
        meters_per_degree_lng = meters_per_degree_lat * math.cos(math.radians(clamped_lat))
        lng_offset = (distance_meters * math.sin(angle)) / meters_per_degree_lng if meters_per_degree_lng > 0.01 else 0

        return (base_lat + lat_offset, base_lng + lng_offset)
    
    for member in members_qs:
        # Créer une clé de cache basée sur l'adresse
        base_address = (member.address or '').strip() or ((member.family.address or '').strip() if member.family else '')
        base_city = (member.city or '').strip() or ((member.family.city or '').strip() if member.family else '') or ((member.site.city or '').strip() if member.site else '')
        base_postal_code = (member.postal_code or '').strip() or ((member.family.postal_code or '').strip() if member.family else '')
        cache_key = f"{base_address}|{base_city}|{base_postal_code}"
        
        if cache_key in geocode_cache:
            coords = geocode_cache[cache_key]
        else:
            coords = geocode_address(
                address=base_address,
                city=base_city,
                postal_code=base_postal_code
            )
            geocode_cache[cache_key] = coords

        if not coords and member.family and member.family.latitude is not None and member.family.longitude is not None:
            coords = (float(member.family.latitude), float(member.family.longitude))

        if not coords and member.site and member.site.latitude is not None and member.site.longitude is not None:
            coords = (float(member.site.latitude), float(member.site.longitude))

        if not coords and member.family and member.family.neighborhood and member.family.neighborhood.city:
            city_obj = member.family.neighborhood.city
            if city_obj.latitude is not None and city_obj.longitude is not None:
                coords = deterministic_offset_coords(float(city_obj.latitude), float(city_obj.longitude), f"cityobj:{city_obj.id}:member:{member.id}")

        if not coords and base_city:
            city_key = base_city.strip().lower()
            if city_key in city_coords:
                coords = deterministic_offset_coords(city_coords[city_key][0], city_coords[city_key][1], f"cityname:{city_key}:member:{member.id}")

        # Fallback final: si adresse présente mais aucun géocodage possible, placer autour de Cayenne
        if not coords and base_address:
            coords = deterministic_offset_coords(4.9225, -52.3058, f"default:{member.id}", min_offset_meters=300, max_offset_meters=2500)
        
        if coords:
            # Appliquer l'obfuscation si nécessaire
            if obfuscate:
                display_lat, display_lng = obfuscate_coordinates(coords[0], coords[1])
            elif member.site and member.site.latitude is not None and member.site.longitude is not None and coords == (float(member.site.latitude), float(member.site.longitude)):
                display_lat, display_lng = obfuscate_coordinates(coords[0], coords[1], min_offset_meters=120, max_offset_meters=250)
            else:
                display_lat, display_lng = coords[0], coords[1]
            
            members_data.append({
                'type': 'member',
                'id': member.id,
                'name': member.full_name,
                'lat': display_lat,
                'lng': display_lng,
                'address': base_address,
                'city': base_city,
                'phone': member.phone or '',
                'status': member.status,
                'site': member.site.name if member.site else '',
                'family': member.family.name if member.family else '',
                'obfuscated': obfuscate,  # Indicateur pour le frontend
            })
    
    # Statistiques
    total_members = Member.objects.count()
    members_with_address = Member.objects.filter(
        (Q(address__isnull=False) & ~Q(address='')) |
        (Q(family__address__isnull=False) & ~Q(family__address='')) |
        (Q(family__latitude__isnull=False) & Q(family__longitude__isnull=False))
    ).count()
    members_geocoded = len(members_data)
    
    # Villes uniques pour le filtre
    member_cities = Member.objects.exclude(
        Q(city__isnull=True) | Q(city='')
    ).values_list('city', flat=True)
    family_cities = Family.objects.exclude(
        Q(city__isnull=True) | Q(city='')
    ).values_list('city', flat=True)
    cities = sorted(set(list(member_cities) + list(family_cities)))
    
    return JsonResponse({
        'sites': sites_data,
        'members': members_data,
        'cities': cities,
        'stats': {
            'total_members': total_members,
            'members_with_address': members_with_address,
            'members_geocoded': members_geocoded,
        }
    })
