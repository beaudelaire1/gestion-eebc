"""Le référencement du site vitrine ne doit pas se dégrader en silence.

Une balise canonique qui recopie les paramètres de tracking, un JSON-LD cassé
par une apostrophe, un titre qui perd la mention du territoire : rien de tout
cela ne provoque d'erreur visible. Seuls des tests le signalent.
"""

import json
import re

import pytest
from django.urls import reverse

from apps.core import seo
from apps.core.models import Site, SiteSettings


JSON_LD = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL
)

# Pages publiques qui doivent porter la requête cible.
PUBLIC_PAGES = [
    'public:home',
    'public:sites',
    'public:news_list',
    'public:events_list',
    'public:contact',
    'public:map',
    'public:register',
]


@pytest.fixture
def church(db):
    SiteSettings.objects.all().delete()
    settings_obj = SiteSettings.get_settings()
    settings_obj.site_name = 'EEBC'
    settings_obj.save()
    Site.objects.create(
        code='CAB',
        name='Cabassou',
        address="11 lot Calimbé 2, rte de Cabassou",
        city='Cayenne',
        postal_code='97300',
        latitude='4.918944',
        longitude='-52.313694',
        is_active=True,
    )
    return settings_obj


def _payloads(html):
    """Tous les blocs de données structurées de la page, désérialisés.

    ``json.loads`` échoue si un titre contenant une apostrophe ou un chevron a
    été inséré sans échappement — c'est exactement ce que l'on veut détecter.
    """
    return [json.loads(block) for block in JSON_LD.findall(html)]


@pytest.mark.parametrize('url_name', PUBLIC_PAGES)
def test_public_page_titles_name_the_territory(client, church, url_name):
    """Sans « Guyane » dans le titre, la page ne peut pas gagner la requête."""
    html = client.get(reverse(url_name)).content.decode()

    title = re.search(r'<title>(.*?)</title>', html, re.DOTALL).group(1)
    assert 'Guyane' in title, f"{url_name} : {title}"


@pytest.mark.parametrize('url_name', PUBLIC_PAGES)
def test_public_page_has_a_non_empty_description(client, church, url_name):
    html = client.get(reverse(url_name)).content.decode()

    description = re.search(
        r'<meta name="description" content="(.*?)">', html, re.DOTALL
    ).group(1)
    assert len(description) > 60, f"{url_name} : {description!r}"
    assert len(description) < 250, f"{url_name} : description trop longue"


@pytest.mark.parametrize('url_name', PUBLIC_PAGES)
def test_open_graph_values_are_never_empty(client, church, url_name):
    """Le repli reposait sur ``block.super``, qui ne rend rien depuis le parent."""
    html = client.get(reverse(url_name)).content.decode()

    for prop in ('og:title', 'og:description', 'og:image'):
        value = re.search(
            rf'<meta property="{prop}" content="(.*?)">', html, re.DOTALL
        ).group(1)
        assert value.strip(), f"{url_name} : {prop} vide"

    image = re.search(
        r'<meta property="og:image" content="(.*?)">', html, re.DOTALL
    ).group(1)
    assert image.startswith('http'), "og:image doit être une URL absolue"


def test_canonical_drops_tracking_parameters(client, church):
    """Un lien tracké ne doit pas créer une seconde URL pour le même contenu."""
    url = reverse('public:sites')
    html = client.get(url, {'utm_source': 'facebook', 'fbclid': 'x'}).content.decode()

    canonical = re.search(
        r'<link rel="canonical" href="(.*?)">', html, re.DOTALL
    ).group(1)
    assert canonical.endswith(url)
    assert 'utm_source' not in canonical
    assert 'fbclid' not in canonical


def test_canonical_keeps_the_content_bearing_parameters(rf):
    """La page 2 et un filtre de catégorie restent des URL distinctes.

    Les rabattre sur la page 1 reviendrait à retirer leur contenu de l'index.
    """
    request = rf.get('/actualites/', {'page': '2', 'utm_medium': 'mail'})

    canonical = seo.canonical_url(request)

    assert canonical.endswith('/actualites/?page=2')
    assert 'utm_medium' not in canonical


@pytest.mark.parametrize('url_name', PUBLIC_PAGES)
def test_structured_data_is_valid_json(client, church, url_name):
    html = client.get(reverse(url_name)).content.decode()

    payloads = _payloads(html)
    assert payloads, f"{url_name} : aucune donnée structurée"


def test_the_home_page_declares_a_geolocated_church(client, church):
    """Sans adresse ni coordonnées, aucune chance d'apparaître en recherche locale."""
    html = client.get(reverse('public:home')).content.decode()

    graph = next(p for p in _payloads(html) if '@graph' in p)['@graph']
    organization = next(n for n in graph if n['@id'].endswith('#organization'))

    assert organization['@type'] == 'Church'
    assert organization['address']['addressCountry'] == seo.COUNTRY_CODE
    assert organization['address']['addressLocality'] == 'Cayenne'
    assert organization['geo']['latitude'] == pytest.approx(4.918944)
    assert seo.REGION_FULL in json.dumps(organization, ensure_ascii=False)


def test_each_place_is_linked_to_the_organization(client, church):
    """Les lieux doivent pendre de l'organisation, pas flotter isolément."""
    html = client.get(reverse('public:home')).content.decode()

    graph = next(p for p in _payloads(html) if '@graph' in p)['@graph']
    places = [n for n in graph if n['@id'].endswith('#CAB')]

    assert places, "le site Cabassou n'apparaît pas dans le graphe"
    assert places[0]['parentOrganization']['@id'].endswith('#organization')


def test_inner_pages_expose_a_breadcrumb(client, church):
    """L'accueil n'en a pas besoin ; une page interne, si."""
    home = client.get(reverse('public:home')).content.decode()
    inner = client.get(reverse('public:sites')).content.decode()

    assert not [p for p in _payloads(home) if p.get('@type') == 'BreadcrumbList']
    trail = next(p for p in _payloads(inner) if p.get('@type') == 'BreadcrumbList')
    assert [item['name'] for item in trail['itemListElement']] == [
        'Accueil', 'Nos églises'
    ]


def test_transactional_pages_are_not_indexed(client, church):
    """Une page « merci pour votre don » n'a rien à faire dans les résultats."""
    html = client.get(reverse('public:donation_cancel')).content.decode()

    robots = re.findall(r'<meta name="robots" content="(.*?)">', html)
    assert robots == ['noindex, follow'], robots


def test_robots_points_to_the_sitemap(client):
    body = client.get('/robots.txt').content.decode()

    assert body.rstrip().endswith('/sitemap.xml')
    assert 'Disallow: /admin/' in body


def test_sitemap_only_uses_https(client, church):
    """Les URL du plan doivent coïncider avec les canoniques, sinon tout double."""
    body = client.get('/sitemap.xml').content.decode()

    assert '<loc>http://' not in body
    assert '<loc>https://' in body


def test_the_serializer_neutralises_a_closing_script_tag():
    """Un titre malveillant ou maladroit ne doit pas fermer la balise."""
    rendered = seo.dumps({'name': '</script><img src=x>'})

    assert '</script>' not in rendered
    assert json.loads(rendered.replace('<\\/', '</'))['name'] == '</script><img src=x>'
