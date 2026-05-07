"""
Vues admin personnalisées pour les membres.
Inclut une carte interactive des membres par quartier/famille.
"""
import math
import hashlib
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Q

from .models import Member
from .geocoding import (
    geocode_address_with_metadata,
    build_canonical_address,
    deterministic_offset_coords as stable_offset_coords,
    house_number_offset_coords,
    is_valid_geocoded_coords,
    normalize_address_component,
    street_key_from_address,
)
from apps.core.models import Site, Neighborhood, Family, City
from apps.core.permissions import role_required, has_role


logger = logging.getLogger(__name__)


# =============================================================================
# GPS OBFUSCATION UTILITIES
# =============================================================================

def obfuscate_coordinates(lat, lng, member_id=None, address_seed=None, min_offset_meters=8, max_offset_meters=15):
    """
    Ajoute un décalage déterministe aux coordonnées GPS pour protéger la vie privée.
    L'offset est basé sur l'adresse (même adresse = même point) + micro-jitter par membre.
    """
    METERS_PER_DEGREE_LAT = 111320

    # Seed principal basé sur l'adresse pour grouper les membres de la même adresse
    primary_seed = str(address_seed or f"{lat:.6f},{lng:.6f}")
    primary_hash = hashlib.sha256(primary_seed.encode('utf-8')).hexdigest()
    angle = (int(primary_hash[:8], 16) / 0xFFFFFFFF) * 2 * math.pi
    distance_meters = min_offset_meters + (int(primary_hash[8:16], 16) / 0xFFFFFFFF) * (max_offset_meters - min_offset_meters)

    lat_offset = (distance_meters * math.cos(angle)) / METERS_PER_DEGREE_LAT
    clamped_lat = max(-89.9, min(89.9, lat))
    meters_per_degree_lng = METERS_PER_DEGREE_LAT * math.cos(math.radians(clamped_lat))
    lng_offset = (distance_meters * math.sin(angle)) / meters_per_degree_lng if meters_per_degree_lng > 0.01 else 0

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
    return not (
        user
        and user.is_authenticated
        and (user.is_superuser or user.has_role('admin'))
    )


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
    
    # Données des membres avec adresse ou rattachés à un site géolocalisé
    members_data = []
    members_qs = Member.objects.filter(
        (Q(address__isnull=False) & ~Q(address='')) |
        (Q(family__address__isnull=False) & ~Q(family__address='')) |
        (Q(family__latitude__isnull=False) & Q(family__longitude__isnull=False)) |
        (Q(site__latitude__isnull=False) & Q(site__longitude__isnull=False))  # fallback: coordonnées du site
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
        normalize_address_component(c.name): (float(c.latitude), float(c.longitude))
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

    def street_fallback_coords(base_lat, base_lng, city_seed, base_address, address_key):
        street_key = street_key_from_address(base_address)
        if not street_key:
            return deterministic_offset_coords(
                base_lat,
                base_lng,
                f"city:{city_seed}:addr:{address_key}",
                min_offset_meters=80,
                max_offset_meters=220,
            )

        street_anchor = stable_offset_coords(
            base_lat,
            base_lng,
            f"city:{city_seed}:street:{street_key}",
            min_offset_meters=80,
            max_offset_meters=700,
        )
        return house_number_offset_coords(
            street_anchor[0],
            street_anchor[1],
            base_address,
            min_offset_meters=2,
            max_offset_meters=90,
        )
    
    for member in members_qs:
        base_address = (member.address or '').strip() or ((member.family.address or '').strip() if member.family else '')
        base_city = (member.city or '').strip() or ((member.family.city or '').strip() if member.family else '') or ((member.site.city or '').strip() if member.site else '')
        base_postal_code = (member.postal_code or '').strip() or ((member.family.postal_code or '').strip() if member.family else '')

        canonical = build_canonical_address(
            address=base_address,
            city=base_city,
            postal_code=base_postal_code,
        )
        address_key = canonical['address_key']
        
        if address_key in geocode_cache:
            coords = geocode_cache[address_key]
        else:
            geocode_result = geocode_address_with_metadata(
                address=base_address,
                city=base_city,
                postal_code=base_postal_code,
            )
            coords = geocode_result['coords']
            if coords and not is_valid_geocoded_coords(coords[0], coords[1], base_city):
                logger.warning(
                    "members_map_reject_invalid_geocode member=%s key=%s coords=%s",
                    member.id,
                    address_key[:12],
                    coords,
                )
                coords = None
            geocode_cache[address_key] = coords
            logger.info(
                "members_map_geocode member=%s key=%s from_cache=%s",
                member.id,
                address_key[:12],
                geocode_result.get('from_cache', False),
            )

        if not coords and member.family and member.family.latitude is not None and member.family.longitude is not None:
            family_coords = (float(member.family.latitude), float(member.family.longitude))
            if is_valid_geocoded_coords(family_coords[0], family_coords[1], base_city):
                coords = family_coords

        # NE PAS utiliser les coordonnées du site comme fallback
        # (sinon le membre apparaît à l'église au lieu de chez lui)

        if not coords and member.family and member.family.neighborhood and member.family.neighborhood.city:
            city_obj = member.family.neighborhood.city
            if city_obj.latitude is not None and city_obj.longitude is not None:
                coords = street_fallback_coords(
                    float(city_obj.latitude),
                    float(city_obj.longitude),
                    f"cityobj:{city_obj.id}",
                    base_address,
                    address_key,
                )

        if not coords and base_city:
            city_key = normalize_address_component(base_city)
            if city_key in city_coords:
                coords = street_fallback_coords(
                    city_coords[city_key][0],
                    city_coords[city_key][1],
                    f"cityname:{city_key}",
                    base_address,
                    address_key,
                )

        # Pas de fallback par défaut : si on ne peut pas géolocaliser, on n'affiche pas
        
        if coords and is_valid_geocoded_coords(coords[0], coords[1], base_city):
            # Appliquer l'obfuscation si nécessaire (déterministe : même adresse = même position)
            if obfuscate:
                display_lat, display_lng = obfuscate_coordinates(
                    coords[0], coords[1],
                    address_seed=address_key,
                )
            else:
                # Admin / secrétariat : afficher la position exacte
                # (même adresse = même point sur la carte)
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
                'location_key': address_key,
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
