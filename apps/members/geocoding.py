"""
Service de géocodage pour convertir les adresses en coordonnées GPS.
Utilise l'API Nominatim (OpenStreetMap) - gratuite et sans clé API.
"""
import requests
import time
from functools import lru_cache


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "EEBC-Gestion/1.0"


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
    if not address and not city:
        return None
    
    # Nettoyer le code postal (enlever .0 si présent)
    if postal_code:
        postal_code = str(postal_code).replace('.0', '').strip()
    
    # Construire la requête
    query_parts = []
    if address:
        query_parts.append(address)
    if city:
        query_parts.append(city)
    if postal_code:
        query_parts.append(postal_code)
    query_parts.append(country)
    
    query = ", ".join(query_parts)
    
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                'q': query,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1,
            },
            headers={
                'User-Agent': USER_AGENT
            },
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            if results:
                lat = float(results[0]['lat'])
                lon = float(results[0]['lon'])
                return (lat, lon)
        
        return None
        
    except Exception as e:
        print(f"Erreur géocodage: {e}")
        return None


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
