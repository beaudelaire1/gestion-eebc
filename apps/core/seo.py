"""Référencement naturel du site vitrine.

Les balises de tête et les données structurées étaient écrites à la main dans
chaque gabarit : une accolade oubliée dans un JSON-LD, une URL relative dans une
balise Open Graph, et Google écarte silencieusement la page. Tout est donc
sérialisé ici avec ``json.dumps`` et des URL absolues construites depuis la
requête.

La requête cible est « église évangélique en Guyane » : les libellés par défaut
associent systématiquement la dénomination, la ville et le territoire, car un
titre qui ne contient pas le lieu ne peut pas gagner une recherche locale.
"""

import json

from apps.core.church import CHURCH_INFO

# Territoire visé. Employé dans les titres, les descriptions et les balises geo.
REGION = "Guyane"
REGION_FULL = "Guyane française"
COUNTRY_CODE = "GF"
DEFAULT_CITY = "Cayenne"

BRAND = CHURCH_INFO['name']
BRAND_SHORT = "EEBC"

# Repli de description : 155 caractères environ, la requête cible en tête.
DEFAULT_META_DESCRIPTION = (
    "Église évangélique baptiste en Guyane française : cultes du dimanche à "
    "Cayenne (Cabassou) et Macouria. Horaires, événements, contact et vie de "
    "l'église."
)

DEFAULT_TITLE = (
    f"Église évangélique en {REGION} — {BRAND_SHORT}, Cayenne et Macouria"
)

# Paramètres d'URL qui désignent réellement un contenu distinct. Tout le reste
# (utm_*, fbclid, gclid…) duplique la page et doit disparaître du canonique.
CANONICAL_QUERY_PARAMS = ('page', 'category')

# schema.org attend un jour nommé ; WorshipSchedule stocke 1 (lundi) à 7.
_SCHEMA_DAYS = {
    1: "https://schema.org/Monday",
    2: "https://schema.org/Tuesday",
    3: "https://schema.org/Wednesday",
    4: "https://schema.org/Thursday",
    5: "https://schema.org/Friday",
    6: "https://schema.org/Saturday",
    7: "https://schema.org/Sunday",
}


def site_root(request):
    """Racine absolue du site, sans barre oblique finale."""
    return f"{request.scheme}://{request.get_host()}"


def absolute_url(request, path):
    """URL absolue à partir d'un chemin ou d'une URL déjà absolue.

    Open Graph et JSON-LD refusent les chemins relatifs : une image de partage
    servie en ``/media/...`` n'apparaît sur aucun réseau social.
    """
    if not path:
        return ""
    if path.startswith(('http://', 'https://')):
        return path
    return f"{site_root(request)}{path}"


def canonical_url(request):
    """URL canonique : chemin + seuls les paramètres porteurs de contenu.

    ``request.build_absolute_uri()`` recopiait la chaîne de requête entière ;
    chaque lien tracké générait donc une URL concurrente de la page d'origine.
    """
    base = f"{site_root(request)}{request.path}"
    kept = [
        (key, request.GET[key])
        for key in CANONICAL_QUERY_PARAMS
        if request.GET.get(key)
    ]
    if not kept:
        return base
    query = "&".join(f"{key}={value}" for key, value in kept)
    return f"{base}?{query}"


def _postal_address(site):
    address = {
        "@type": "PostalAddress",
        "addressCountry": COUNTRY_CODE,
        "addressRegion": REGION_FULL,
    }
    if site.address:
        address["streetAddress"] = " ".join(site.address.split())
    if site.city:
        address["addressLocality"] = site.city
    if getattr(site, 'postal_code', ''):
        address["postalCode"] = site.postal_code
    return address


def _opening_hours(site):
    """Horaires de culte au format schema.org.

    Ce sont eux qui alimentent l'encart « Horaires » du résultat Google : sans
    eux, une recherche « culte dimanche Cayenne » n'a rien à afficher.
    """
    specs = []
    for schedule in getattr(site, 'worship_schedules_list', []).all():
        day = _SCHEMA_DAYS.get(schedule.day_of_week)
        if not day:
            continue
        spec = {
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": day,
            "opens": schedule.start_time.strftime("%H:%M"),
            "name": schedule.name,
        }
        if schedule.end_time:
            spec["closes"] = schedule.end_time.strftime("%H:%M")
        specs.append(spec)
    return specs


def _social_profiles(site_settings):
    urls = [
        getattr(site_settings, 'facebook_url', ''),
        getattr(site_settings, 'youtube_url', ''),
        getattr(site_settings, 'instagram_url', ''),
    ]
    return [url for url in urls if url]


def church_place(request, site, site_settings, logo_url):
    """Fiche d'un lieu de culte : adresse, GPS, horaires.

    Une entrée par site donne à Google une entité géolocalisée par commune, ce
    qu'une organisation unique avec trois adresses ne produit pas.
    """
    root = site_root(request)
    place = {
        "@type": "Church",
        "@id": f"{root}/nos-eglises/#{site.code}",
        "name": site.name,
        "parentOrganization": {"@id": f"{root}/#organization"},
        "address": _postal_address(site),
        "areaServed": {
            "@type": "AdministrativeArea",
            "name": REGION_FULL,
        },
        "url": f"{root}/nos-eglises/",
    }
    if logo_url:
        place["image"] = logo_url
    if site.latitude is not None and site.longitude is not None:
        place["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": float(site.latitude),
            "longitude": float(site.longitude),
        }
        place["hasMap"] = (
            f"https://www.google.com/maps/search/?api=1&query="
            f"{site.latitude},{site.longitude}"
        )
    if site.phone:
        place["telephone"] = site.phone
    elif getattr(site_settings, 'phone', ''):
        place["telephone"] = site_settings.phone
    if site.email:
        place["email"] = site.email
    hours = _opening_hours(site)
    if hours:
        place["openingHoursSpecification"] = hours
    return place


def organization_graph(request, site_settings, sites, logo_url):
    """Graphe JSON-LD global : église, site web, lieux de culte.

    Un seul ``@graph`` relié par ``@id`` vaut mieux que trois scripts isolés :
    Google rattache alors le site web, l'organisation et chaque lieu à la même
    entité au lieu d'en déduire trois entités sans lien.
    """
    root = site_root(request)
    description = (
        getattr(site_settings, 'meta_description', '') or DEFAULT_META_DESCRIPTION
    )
    name = getattr(site_settings, 'site_name', '') or BRAND_SHORT

    organization = {
        "@type": "Church",
        "@id": f"{root}/#organization",
        "name": name,
        "alternateName": [BRAND, BRAND_SHORT],
        "url": f"{root}/",
        "description": description,
        "areaServed": [
            {"@type": "AdministrativeArea", "name": REGION_FULL},
            {"@type": "City", "name": DEFAULT_CITY},
        ],
        "knowsLanguage": ["fr-FR"],
    }
    if logo_url:
        organization["logo"] = {
            "@type": "ImageObject",
            "@id": f"{root}/#logo",
            "url": logo_url,
        }
        organization["image"] = {"@id": f"{root}/#logo"}

    phone = getattr(site_settings, 'phone', '') or CHURCH_INFO['phone']
    if phone:
        organization["telephone"] = phone
    email = getattr(site_settings, 'email', '') or CHURCH_INFO['email']
    if email:
        organization["email"] = email

    profiles = _social_profiles(site_settings)
    if profiles:
        organization["sameAs"] = profiles

    places = [church_place(request, site, site_settings, logo_url) for site in sites]
    if places:
        organization["location"] = [{"@id": place["@id"]} for place in places]
        # L'adresse principale reste celle du premier site, exigée par Google
        # pour rattacher l'organisation à une fiche établissement.
        organization["address"] = places[0]["address"]
        if "geo" in places[0]:
            organization["geo"] = places[0]["geo"]

    website = {
        "@type": "WebSite",
        "@id": f"{root}/#website",
        "url": f"{root}/",
        "name": name,
        "description": description,
        "inLanguage": "fr-FR",
        "publisher": {"@id": f"{root}/#organization"},
    }

    return {"@context": "https://schema.org", "@graph": [organization, website] + places}


def article_graph(request, article, site_settings, logo_url):
    """Article d'actualité au format ``NewsArticle``.

    ``dateModified`` et un éditeur muni de son logo sont exigés par Google pour
    l'éligibilité aux résultats enrichis : sans eux l'article reste un lien nu.
    """
    root = site_root(request)
    url = f"{root}{request.path}"
    name = getattr(site_settings, 'site_name', '') or BRAND_SHORT

    payload = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "@id": f"{url}#article",
        "headline": article.title[:110],
        "name": article.title,
        "url": url,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "inLanguage": "fr-FR",
        "isAccessibleForFree": True,
        "publisher": {"@id": f"{root}/#organization"},
        "author": {
            "@type": "Person",
            "name": (
                getattr(article, 'display_author', '')
                or getattr(article, 'author_name', '')
                or name
            ),
        },
    }
    if article.excerpt:
        payload["description"] = " ".join(article.excerpt.split())[:300]
    if article.publish_date:
        payload["datePublished"] = article.publish_date.isoformat()
    updated = getattr(article, 'updated_at', None)
    payload["dateModified"] = (
        updated.isoformat() if updated else payload.get("datePublished", "")
    )
    image = getattr(article, 'featured_image', None)
    payload["image"] = absolute_url(request, image.url) if image else logo_url
    if getattr(article, 'category', ''):
        payload["articleSection"] = article.get_category_display()
    return payload


def event_graph(request, event, site_settings, logo_url):
    """Événement au format ``Event``, lieu géolocalisé compris.

    Un événement sans ``location`` structurée n'apparaît pas dans le panneau
    « événements » de Google ; l'adresse du site organisateur sert de repli.
    """
    root = site_root(request)
    url = f"{root}{request.path}"

    start = event.start_date.isoformat()
    if event.start_time:
        start = f"{event.start_date.isoformat()}T{event.start_time.strftime('%H:%M')}"

    payload = {
        "@context": "https://schema.org",
        "@type": "Event",
        "@id": f"{url}#event",
        "name": event.title,
        "url": url,
        "startDate": start,
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "inLanguage": "fr-FR",
        "organizer": {"@id": f"{root}/#organization"},
        "isAccessibleForFree": True,
    }
    if event.description:
        payload["description"] = " ".join(event.description.split())[:500]
    if event.end_date:
        end = event.end_date.isoformat()
        if event.end_time:
            end = f"{event.end_date.isoformat()}T{event.end_time.strftime('%H:%M')}"
        payload["endDate"] = end
    image = getattr(event, 'image', None)
    payload["image"] = absolute_url(request, image.url) if image else logo_url

    site = getattr(event, 'site', None)
    place = {
        "@type": "Place",
        "name": event.location or (site.name if site else BRAND),
    }
    if event.address:
        place["address"] = {
            "@type": "PostalAddress",
            "streetAddress": " ".join(event.address.split()),
            "addressCountry": COUNTRY_CODE,
            "addressRegion": REGION_FULL,
        }
    elif site is not None:
        place["address"] = _postal_address(site)
        if site.latitude is not None and site.longitude is not None:
            place["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": float(site.latitude),
                "longitude": float(site.longitude),
            }
    else:
        place["address"] = {
            "@type": "PostalAddress",
            "addressLocality": DEFAULT_CITY,
            "addressCountry": COUNTRY_CODE,
            "addressRegion": REGION_FULL,
        }
    payload["location"] = place
    return payload


def breadcrumb_graph(request, trail):
    """Fil d'Ariane JSON-LD.

    Google remplace l'URL brute du résultat par ce chemin : « eglise-ebc.org ›
    Nos églises » se lit mieux qu'une URL et gagne des clics.
    """
    root = site_root(request)
    items = []
    for position, (label, path) in enumerate(trail, start=1):
        item = {
            "@type": "ListItem",
            "position": position,
            "name": label,
        }
        if path:
            item["item"] = absolute_url(request, path)
        items.append(item)
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "@id": f"{root}{request.path}#breadcrumb",
        "itemListElement": items,
    }


def dumps(payload):
    """Sérialise un graphe pour insertion dans un ``<script>``.

    ``</`` est neutralisé : une description contenant ``</script>`` fermerait
    la balise et casserait la page.
    """
    return escape_script(json.dumps(payload, ensure_ascii=False, indent=None))


def escape_script(raw):
    return raw.replace('</', '<\\/')


def meta_description(site_settings):
    return getattr(site_settings, 'meta_description', '') or DEFAULT_META_DESCRIPTION


def geo_tags(sites):
    """Coordonnées de la balise ``ICBM`` / ``geo.position``.

    Ces balises restent lues par plusieurs annuaires locaux et par Bing ; elles
    coûtent trois lignes et ancrent le site sur la Guyane.
    """
    for site in sites:
        if site.latitude is not None and site.longitude is not None:
            return {
                'position': f"{site.latitude};{site.longitude}",
                'icbm': f"{site.latitude}, {site.longitude}",
                'placename': site.city or DEFAULT_CITY,
            }
    return {'position': '', 'icbm': '', 'placename': DEFAULT_CITY}


__all__ = [
    'REGION', 'REGION_FULL', 'COUNTRY_CODE', 'DEFAULT_CITY',
    'BRAND', 'BRAND_SHORT', 'DEFAULT_META_DESCRIPTION', 'DEFAULT_TITLE',
    'site_root', 'absolute_url', 'canonical_url',
    'organization_graph', 'article_graph', 'event_graph',
    'breadcrumb_graph', 'dumps',
    'meta_description', 'geo_tags',
]
