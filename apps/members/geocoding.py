"""
Service de géocodage pour convertir les adresses en coordonnées GPS.
Utilise l'API Nominatim (OpenStreetMap) - gratuite et sans clé API.
"""
import hashlib
import logging
import math
import re
import unicodedata
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

import requests
import time
from functools import lru_cache
from django.utils import timezone

from .models import GeocodedAddress


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
API_ADRESSE_URL = "https://api-adresse.data.gouv.fr/search/"
USER_AGENT = "EEBC-Gestion/1.0"
GEOCODE_TTL_DAYS = 180
MIN_API_ADRESSE_SCORE = 0.35
MAX_CITY_DISTANCE_KM = 30
FRENCH_GUIANA_BOUNDS = {
    'min_lat': 2.0,
    'max_lat': 6.0,
    'min_lon': -54.8,
    'max_lon': -51.5,
}
FRENCH_GUIANA_CITY_CENTERS = {
    'cayenne': (4.9333, -52.3333),
    'matoury': (4.8486, -52.3314),
    'remire montjoly': (4.9167, -52.2667),
    'remire': (4.9167, -52.2667),
    'montjoly': (4.9167, -52.2667),
    'kourou': (5.1597, -52.6503),
    'macouria': (5.0136, -52.4747),
    'montsinery tonnegrande': (4.8833, -52.4833),
    'roura': (4.7300, -52.3270),
}
EXACT_PROVIDER_TYPES = {'housenumber', 'house', 'building', 'residential'}
STREET_PROVIDER_TYPES = {'street', 'road', 'secondary', 'tertiary', 'primary', 'residential_road'}

logger = logging.getLogger(__name__)


def _is_in_french_guiana_bounds(lat, lon):
    lat = float(lat)
    lon = float(lon)
    return (
        FRENCH_GUIANA_BOUNDS['min_lat'] <= lat <= FRENCH_GUIANA_BOUNDS['max_lat']
        and FRENCH_GUIANA_BOUNDS['min_lon'] <= lon <= FRENCH_GUIANA_BOUNDS['max_lon']
    )


def _distance_km_between(lat_a, lon_a, lat_b, lon_b):
    radius_km = 6371.0
    lat_a_rad = math.radians(float(lat_a))
    lat_b_rad = math.radians(float(lat_b))
    delta_lat = math.radians(float(lat_b) - float(lat_a))
    delta_lon = math.radians(float(lon_b) - float(lon_a))
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a_rad) * math.cos(lat_b_rad) * math.sin(delta_lon / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


def _is_reasonable_for_city(lat, lon, city):
    city_key = normalize_address_component(city)
    center = FRENCH_GUIANA_CITY_CENTERS.get(city_key)
    return not center or _distance_km_between(lat, lon, center[0], center[1]) <= MAX_CITY_DISTANCE_KM


def is_valid_geocoded_coords(lat, lon, city=""):
    """Valide les coordonnées avant cache/affichage."""
    try:
        lat_float = float(lat)
        lon_float = float(lon)
    except (TypeError, ValueError):
        return False
    return _is_in_french_guiana_bounds(lat_float, lon_float) and _is_reasonable_for_city(
        lat_float,
        lon_float,
        city,
    )


STREET_ABBREVIATIONS = {
    r"\bav\.?\b": "avenue",
    r"\bbd\.?\b": "boulevard",
    r"\brte\.?\b": "route",
    r"\bste\b": "sainte",
    r"\bst\b": "saint",
    r"\bimp\.?\b": "impasse",
    r"\bpl\.?\b": "place",
    r"\bch\.?\b": "chemin",
}


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', value)
    return ''.join(c for c in normalized if not unicodedata.combining(c))


def normalize_address_component(value: str) -> str:
    """Normalise une composante d'adresse de manière déterministe."""
    if not value:
        return ""

    cleaned = _strip_accents(f"{value}").lower().strip()
    cleaned = re.sub(r"\b(n|no|nº|n°|numero)\s*", ' ', cleaned)
    cleaned = re.sub(r"[,'’\.\-_/;:]+", ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def normalize_street_address(address: str) -> str:
    """Normalise les abréviations de voirie pour stabiliser le géocodage."""
    normalized = normalize_address_component(address)
    if not normalized:
        return ""

    for pattern, replacement in STREET_ABBREVIATIONS.items():
        normalized = re.sub(pattern, replacement, normalized)

    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def extract_house_number(address: str):
    normalized = normalize_street_address(address)
    match = re.search(r"\b\d{1,5}\b", normalized)
    return int(match.group(0)) if match else None


def street_key_from_address(address: str) -> str:
    normalized = normalize_street_address(address)
    normalized = re.sub(r"\b\d{1,5}\b", ' ', normalized)
    normalized = re.sub(r"\b(bis|ter|quater|batiment|bat|appartement|appt|lot|logement)\b", ' ', normalized)
    return re.sub(r'\s+', ' ', normalized).strip()


def deterministic_offset_coords(base_lat, base_lng, seed_value, min_offset_meters=8, max_offset_meters=15):
    meters_per_degree_lat = 111320
    seed = hashlib.sha256(str(seed_value).encode('utf-8')).hexdigest()
    angle = (int(seed[:8], 16) / 0xFFFFFFFF) * 2 * math.pi
    distance_meters = min_offset_meters + (
        (int(seed[8:16], 16) / 0xFFFFFFFF) * (max_offset_meters - min_offset_meters)
    )

    lat_offset = (distance_meters * math.cos(angle)) / meters_per_degree_lat
    clamped_lat = max(-89.9, min(89.9, float(base_lat)))
    meters_per_degree_lng = meters_per_degree_lat * math.cos(math.radians(clamped_lat))
    lng_offset = (distance_meters * math.sin(angle)) / meters_per_degree_lng if meters_per_degree_lng > 0.01 else 0
    return (float(base_lat) + lat_offset, float(base_lng) + lng_offset)


def house_number_offset_coords(base_lat, base_lng, address, min_offset_meters=2, max_offset_meters=80):
    house_number = extract_house_number(address)
    street_key = street_key_from_address(address)
    if not house_number or not street_key:
        return deterministic_offset_coords(base_lat, base_lng, address, min_offset_meters=5, max_offset_meters=25)

    street_seed = hashlib.sha256(street_key.encode('utf-8')).hexdigest()
    angle = (int(street_seed[:8], 16) / 0xFFFFFFFF) * 2 * math.pi
    distance_meters = min_offset_meters + ((house_number % 100) / 99) * (max_offset_meters - min_offset_meters)
    meters_per_degree_lat = 111320
    lat_offset = (distance_meters * math.cos(angle)) / meters_per_degree_lat
    clamped_lat = max(-89.9, min(89.9, float(base_lat)))
    meters_per_degree_lng = meters_per_degree_lat * math.cos(math.radians(clamped_lat))
    lng_offset = (distance_meters * math.sin(angle)) / meters_per_degree_lng if meters_per_degree_lng > 0.01 else 0
    return (float(base_lat) + lat_offset, float(base_lng) + lng_offset)


def nearby_house_offset_coords(base_lat, base_lng, street_key, number_delta):
    if not number_delta or not street_key:
        return (float(base_lat), float(base_lng))

    street_seed = hashlib.sha256(street_key.encode('utf-8')).hexdigest()
    angle = (int(street_seed[:8], 16) / 0xFFFFFFFF) * 2 * math.pi
    if number_delta < 0:
        angle += math.pi
    distance_meters = min(abs(number_delta) * 3, 120)
    meters_per_degree_lat = 111320
    lat_offset = (distance_meters * math.cos(angle)) / meters_per_degree_lat
    clamped_lat = max(-89.9, min(89.9, float(base_lat)))
    meters_per_degree_lng = meters_per_degree_lat * math.cos(math.radians(clamped_lat))
    lng_offset = (distance_meters * math.sin(angle)) / meters_per_degree_lng if meters_per_degree_lng > 0.01 else 0
    return (float(base_lat) + lat_offset, float(base_lng) + lng_offset)


def normalize_postal_code(postal_code: str) -> str:
    """Normalise le code postal en conservant uniquement les chiffres."""
    if not postal_code:
        return ""
    raw = f"{postal_code}".replace('.0', '').strip()
    return re.sub(r'\D', '', raw)


def build_canonical_address(address: str, city: str = "", postal_code: str = "", country: str = "Guyane française"):
    """Construit l'adresse canonique et sa clé déterministe."""
    normalized_address = normalize_street_address(address)
    normalized_city = normalize_address_component(city)
    normalized_postal_code = normalize_postal_code(postal_code)
    normalized_country = normalize_address_component(country) or "guyane francaise"

    parts = [normalized_address, normalized_city, normalized_postal_code, normalized_country]
    canonical = '|'.join(parts)
    address_key = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    query_parts = [p for p in [normalized_address, normalized_city, normalized_postal_code, country] if p]
    query = ', '.join(query_parts)

    return {
        'address_key': address_key,
        'normalized_address': normalized_address,
        'normalized_city': normalized_city,
        'normalized_postal_code': normalized_postal_code,
        'country': country,
        'query': query,
        'has_input': bool(normalized_address or normalized_city),
        'house_number': extract_house_number(address),
        'street_key': street_key_from_address(address),
    }


def build_address_key(address: str, city: str = "", postal_code: str = "", country: str = "Guyane française") -> str:
    """Retourne uniquement la clé d'adresse canonique."""
    return build_canonical_address(address, city, postal_code, country)['address_key']


def _round_coord(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)


def _candidate_is_exact(candidate):
    return candidate['precision'] in EXACT_PROVIDER_TYPES


def _candidate_is_usable(candidate, canonical):
    if not is_valid_geocoded_coords(candidate['lat'], candidate['lon'], canonical['normalized_city']):
        return False
    if (
        canonical['normalized_postal_code']
        and candidate.get('postal_code')
        and normalize_postal_code(candidate['postal_code']) != canonical['normalized_postal_code']
    ):
        return False
    if canonical['normalized_city'] and candidate.get('city'):
        provider_city = normalize_address_component(candidate['city'])
        if canonical['normalized_city'] not in provider_city and provider_city not in canonical['normalized_city']:
            return False
    return True


def _apply_precision_adjustment(candidate, canonical):
    if canonical['house_number'] and not _candidate_is_exact(candidate):
        lat, lon = house_number_offset_coords(
            candidate['lat'],
            candidate['lon'],
            canonical['normalized_address'],
        )
        candidate = {
            **candidate,
            'lat': lat,
            'lon': lon,
            'precision': f"street+number-offset:{candidate['precision']}",
        }
    return candidate


def _api_adresse_candidates(payload):
    if not isinstance(payload, dict):
        return []

    candidates = []
    for feature in payload.get('features') or []:
        geometry = feature.get('geometry') or {}
        props = feature.get('properties') or {}
        coords = geometry.get('coordinates') or []
        if len(coords) < 2:
            continue
        score = float(props.get('score') or 0)
        if score < MIN_API_ADRESSE_SCORE:
            continue
        candidates.append({
            'lat': float(coords[1]),
            'lon': float(coords[0]),
            'provider': 'api-adresse',
            'precision': props.get('type') or '',
            'importance': score,
            'city': props.get('city') or props.get('municipality') or '',
            'postal_code': props.get('postcode') or '',
            'label': props.get('label') or '',
        })
    return candidates


def _nominatim_candidates(payload):
    if not isinstance(payload, list):
        return []

    candidates = []
    for item in payload:
        address = item.get('address') or {}
        try:
            lat = float(item.get('lat'))
            lon = float(item.get('lon'))
        except (TypeError, ValueError):
            continue
        candidates.append({
            'lat': lat,
            'lon': lon,
            'provider': 'nominatim',
            'precision': item.get('type') or item.get('class') or '',
            'importance': float(item.get('importance') or 0),
            'city': address.get('city') or address.get('town') or address.get('village') or address.get('municipality') or '',
            'postal_code': address.get('postcode') or '',
            'label': item.get('display_name') or '',
        })
    return candidates


def _pick_best_candidate(candidates, canonical):
    valid_candidates = [candidate for candidate in candidates if _candidate_is_usable(candidate, canonical)]
    if not valid_candidates:
        return None

    def score(candidate):
        exact = 1 if _candidate_is_exact(candidate) else 0
        postal_match = int(
            bool(canonical['normalized_postal_code'])
            and normalize_postal_code(candidate.get('postal_code') or '') == canonical['normalized_postal_code']
        )
        city_match = int(
            bool(canonical['normalized_city'])
            and canonical['normalized_city'] in normalize_address_component(candidate.get('city') or candidate.get('label') or '')
        )
        return (exact, postal_match, city_match, float(candidate.get('importance') or 0))

    return _apply_precision_adjustment(max(valid_candidates, key=score), canonical)


def _fetch_api_adresse_candidate(canonical):
    params = {
        'q': canonical['query'],
        'limit': 5,
        'autocomplete': 0,
    }
    if canonical['normalized_postal_code']:
        params['postcode'] = canonical['normalized_postal_code']

    response = requests.get(API_ADRESSE_URL, params=params, headers={'User-Agent': USER_AGENT}, timeout=10)
    if response.status_code != 200:
        logger.warning("api_adresse_provider_error status=%s key=%s", response.status_code, canonical['address_key'][:12])
        return None

    payload = response.json()
    if isinstance(payload, list):
        return _pick_best_candidate(_nominatim_candidates(payload), canonical)
    return _pick_best_candidate(_api_adresse_candidates(payload), canonical)


def _fetch_nominatim_candidate(canonical):
    response = requests.get(
        NOMINATIM_URL,
        params={
            'q': canonical['query'],
            'format': 'json',
            'limit': 5,
            'addressdetails': 1,
            'countrycodes': 'gf',
            'accept-language': 'fr',
        },
        headers={'User-Agent': USER_AGENT},
        timeout=10,
    )
    if response.status_code != 200:
        logger.warning("nominatim_provider_error status=%s key=%s", response.status_code, canonical['address_key'][:12])
        return None

    return _pick_best_candidate(_nominatim_candidates(response.json()), canonical)


def _cache_entry_is_usable(cache_entry, canonical):
    if not is_valid_geocoded_coords(
        cache_entry.latitude,
        cache_entry.longitude,
        canonical['normalized_city'],
    ):
        return False

    low_precision = (
        cache_entry.provider_precision in STREET_PROVIDER_TYPES
        or cache_entry.provider_precision.startswith('street+number-offset')
    )
    return not (canonical['house_number'] and low_precision and _same_street_anchor(canonical))


def _same_street_anchor(canonical):
    if not canonical['street_key'] or not canonical['house_number']:
        return None

    queryset = GeocodedAddress.objects.filter(
        normalized_city=canonical['normalized_city'],
        normalized_postal_code=canonical['normalized_postal_code'],
    ).exclude(address_key=canonical['address_key']).only(
        'normalized_address',
        'latitude',
        'longitude',
        'provider_precision',
    )

    anchors = []
    for cache_entry in queryset[:500]:
        if cache_entry.provider_precision not in EXACT_PROVIDER_TYPES:
            continue
        if street_key_from_address(cache_entry.normalized_address) != canonical['street_key']:
            continue
        if not is_valid_geocoded_coords(cache_entry.latitude, cache_entry.longitude, canonical['normalized_city']):
            continue
        house_number = extract_house_number(cache_entry.normalized_address)
        number_delta = abs((house_number or canonical['house_number']) - canonical['house_number'])
        anchors.append((number_delta, float(cache_entry.latitude), float(cache_entry.longitude), house_number))

    if not anchors:
        return None
    _, lat, lon, house_number = min(anchors, key=lambda item: item[0])
    return (lat, lon, house_number)


def _candidate_from_same_street_anchor(canonical):
    anchor = _same_street_anchor(canonical)
    if not anchor:
        return None
    number_delta = canonical['house_number'] - anchor[2]
    lat, lon = nearby_house_offset_coords(
        anchor[0],
        anchor[1],
        canonical['street_key'],
        number_delta,
    )
    return {
        'lat': lat,
        'lon': lon,
        'provider': 'same-street-anchor',
        'precision': 'same-street-anchor',
        'importance': 0,
        'city': canonical['normalized_city'],
        'postal_code': canonical['normalized_postal_code'],
        'label': canonical['query'],
    }


def _fetch_best_candidate(canonical):
    best = _fetch_api_adresse_candidate(canonical) or _fetch_nominatim_candidate(canonical)
    anchored = _candidate_from_same_street_anchor(canonical)
    if not anchored:
        return best
    if not best or not _candidate_is_exact(best):
        return anchored

    distance_from_anchor = _distance_km_between(best['lat'], best['lon'], anchored['lat'], anchored['lon'])
    return anchored if distance_from_anchor > 0.25 else best


def _store_geocode_candidate(canonical, candidate, now):
    lat = _round_coord(candidate['lat'])
    lon = _round_coord(candidate['lon'])
    expires_at = now + timedelta(days=GEOCODE_TTL_DAYS)
    defaults = {
        'normalized_address': canonical['normalized_address'],
        'normalized_city': canonical['normalized_city'],
        'normalized_postal_code': canonical['normalized_postal_code'],
        'country': canonical['country'],
        'latitude': lat,
        'longitude': lon,
        'provider': candidate['provider'],
        'provider_precision': candidate['precision'],
        'provider_importance': Decimal(str(candidate.get('importance') or 0)).quantize(Decimal('0.00001')),
        'raw_query': canonical['query'],
        'expires_at': expires_at,
    }
    GeocodedAddress.objects.update_or_create(
        address_key=canonical['address_key'],
        defaults=defaults,
    )
    return lat, lon


def _geocode_uncached(canonical, now):
    best = _fetch_best_candidate(canonical)
    if best is None:
        logger.info("geocode_no_valid_result key=%s", canonical['address_key'][:12])
        return {
            'coords': None,
            'address_key': canonical['address_key'],
            'from_cache': False,
            'provider': None,
            'precision': None,
        }

    lat = _round_coord(best['lat'])
    lon = _round_coord(best['lon'])
    if not is_valid_geocoded_coords(lat, lon, canonical['normalized_city']):
        logger.warning("geocode_invalid_coords lat=%s lon=%s key=%s", lat, lon, canonical['address_key'][:12])
        return {
            'coords': None,
            'address_key': canonical['address_key'],
            'from_cache': False,
            'provider': best['provider'],
            'precision': best['precision'],
        }

    lat, lon = _store_geocode_candidate(canonical, best, now)
    logger.info(
        "geocode_cache_store key=%s provider=%s precision=%s",
        canonical['address_key'][:12],
        best['provider'],
        best['precision'],
    )
    return {
        'coords': (float(lat), float(lon)),
        'address_key': canonical['address_key'],
        'from_cache': False,
        'provider': best['provider'],
        'precision': best['precision'],
    }


def geocode_address_with_metadata(address, city="", postal_code="", country="Guyane française", force_refresh=False):
    """Géocode une adresse avec cache DB par clé canonique."""
    canonical = build_canonical_address(address=address, city=city, postal_code=postal_code, country=country)
    if not canonical['has_input']:
        return {
            'coords': None,
            'address_key': canonical['address_key'],
            'from_cache': False,
            'provider': None,
            'precision': None,
        }

    now = timezone.now()
    cache_entry = GeocodedAddress.objects.filter(address_key=canonical['address_key']).first()
    if cache_entry and not force_refresh and (cache_entry.expires_at is None or cache_entry.expires_at > now):
        if not _cache_entry_is_usable(cache_entry, canonical):
            logger.warning("geocode_cache_rejected key=%s lat=%s lon=%s", canonical['address_key'][:12], cache_entry.latitude, cache_entry.longitude)
            cache_entry.delete()
        else:
            logger.info("geocode_cache_hit key=%s", canonical['address_key'][:12])
            return {
                'coords': (float(cache_entry.latitude), float(cache_entry.longitude)),
                'address_key': canonical['address_key'],
                'from_cache': True,
                'provider': cache_entry.provider,
                'precision': cache_entry.provider_precision,
            }

    try:
        return _geocode_uncached(canonical, now)
    except Exception:
        logger.exception("geocode_exception key=%s", canonical['address_key'][:12])
        return {
            'coords': None,
            'address_key': canonical['address_key'],
            'from_cache': False,
            'provider': None,
            'precision': None,
        }


@lru_cache(maxsize=500)
def geocode_address(address, city="", postal_code="", country="Guyane française"):
    """
    Convertit une adresse en coordonnées GPS.
    
    Args:
        address: Adresse (rue, numéro)
        city: Ville
        postal_code: Code postal
        country: Pays (défaut: Guyane française)
    
    Returns:
        tuple (latitude, longitude) ou None si non trouvé
    """
    result = geocode_address_with_metadata(
        address=address,
        city=city,
        postal_code=postal_code,
        country=country,
    )
    return result['coords']


def geocode_member(member):
    """
    Géocode l'adresse d'un membre.
    
    Returns:
        tuple (latitude, longitude) ou None
    """
    return geocode_address(
        address=member.address,
        city=member.city,
        postal_code=member.postal_code
    )


def geocode_family(family):
    """
    Géocode l'adresse d'une famille.
    
    Returns:
        tuple (latitude, longitude) ou None
    """
    return geocode_address(
        address=family.address,
        city=family.city,
        postal_code=family.postal_code
    )


def batch_geocode_members(members, delay=1.0):
    """
    Géocode une liste de membres avec délai entre les requêtes.
    (Nominatim limite à 1 requête/seconde)
    
    Args:
        members: QuerySet ou liste de membres
        delay: Délai entre requêtes en secondes
    
    Returns:
        dict {member_id: (lat, lon)}
    """
    results = {}
    
    for member in members:
        if member.address or member.city:
            if coords := geocode_member(member):
                results[member.id] = coords
            time.sleep(delay)  # Respecter la limite de Nominatim
    
    return results
