"""
Service de géocodage pour convertir les adresses en coordonnées GPS.
Utilise l'API Nominatim (OpenStreetMap) - gratuite et sans clé API.
"""
import hashlib
import logging
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
USER_AGENT = "EEBC-Gestion/1.0"
GEOCODE_TTL_DAYS = 180

logger = logging.getLogger(__name__)


STREET_ABBREVIATIONS = {
    r"\bav\.?\b": "avenue",
    r"\bbd\.?\b": "boulevard",
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

    cleaned = _strip_accents(str(value)).lower().strip()
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


def normalize_postal_code(postal_code: str) -> str:
    """Normalise le code postal en conservant uniquement les chiffres."""
    if not postal_code:
        return ""
    raw = str(postal_code).replace('.0', '').strip()
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
    }


def build_address_key(address: str, city: str = "", postal_code: str = "", country: str = "Guyane française") -> str:
    """Retourne uniquement la clé d'adresse canonique."""
    return build_canonical_address(address, city, postal_code, country)['address_key']


def _round_coord(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)


def _pick_best_result(results):
    def score(item):
        importance = float(item.get('importance') or 0)
        place_rank = int(item.get('place_rank') or 0)
        has_house_number = 1 if (item.get('type') in {'house', 'residential', 'building'}) else 0
        return (importance, place_rank, has_house_number)

    return max(results, key=score)


def geocode_address_with_metadata(address, city="", postal_code="", country="Guyane française", force_refresh=False):
    """Géocode une adresse avec cache DB par clé canonique."""
    canonical = build_canonical_address(address=address, city=city, postal_code=postal_code, country=country)
    if not canonical['has_input']:
        return {
            'coords': None,
            'address_key': canonical['address_key'],
            'from_cache': False,
            'provider': None,
        }

    now = timezone.now()
    cache_entry = GeocodedAddress.objects.filter(address_key=canonical['address_key']).first()
    if cache_entry and not force_refresh and (cache_entry.expires_at is None or cache_entry.expires_at > now):
        logger.info("geocode_cache_hit key=%s", canonical['address_key'][:12])
        return {
            'coords': (float(cache_entry.latitude), float(cache_entry.longitude)),
            'address_key': canonical['address_key'],
            'from_cache': True,
            'provider': cache_entry.provider,
        }

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                'q': canonical['query'],
                'format': 'json',
                'limit': 3,
                'addressdetails': 1,
                'countrycodes': 'gf',
                'accept-language': 'fr',
            },
            headers={'User-Agent': USER_AGENT},
            timeout=10,
        )

        if response.status_code != 200:
            logger.warning(
                "geocode_provider_error status=%s key=%s",
                response.status_code,
                canonical['address_key'][:12],
            )
            return {
                'coords': None,
                'address_key': canonical['address_key'],
                'from_cache': False,
                'provider': 'nominatim',
            }

        results = response.json()
        if not results:
            logger.info("geocode_no_result key=%s", canonical['address_key'][:12])
            return {
                'coords': None,
                'address_key': canonical['address_key'],
                'from_cache': False,
                'provider': 'nominatim',
            }

        best = _pick_best_result(results)
        lat = _round_coord(float(best['lat']))
        lon = _round_coord(float(best['lon']))
        expires_at = now + timedelta(days=GEOCODE_TTL_DAYS)

        defaults = {
            'normalized_address': canonical['normalized_address'],
            'normalized_city': canonical['normalized_city'],
            'normalized_postal_code': canonical['normalized_postal_code'],
            'country': canonical['country'],
            'latitude': lat,
            'longitude': lon,
            'provider': 'nominatim',
            'provider_precision': best.get('type', ''),
            'provider_importance': Decimal(str(best.get('importance') or 0)).quantize(Decimal('0.00001')),
            'raw_query': canonical['query'],
            'expires_at': expires_at,
        }

        GeocodedAddress.objects.update_or_create(
            address_key=canonical['address_key'],
            defaults=defaults,
        )

        logger.info("geocode_cache_store key=%s", canonical['address_key'][:12])
        return {
            'coords': (float(lat), float(lon)),
            'address_key': canonical['address_key'],
            'from_cache': False,
            'provider': 'nominatim',
        }
    except Exception:
        logger.exception("geocode_exception key=%s", canonical['address_key'][:12])
        return {
            'coords': None,
            'address_key': canonical['address_key'],
            'from_cache': False,
            'provider': 'nominatim',
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
            coords = geocode_member(member)
            if coords:
                results[member.id] = coords
            time.sleep(delay)  # Respecter la limite de Nominatim
    
    return results
