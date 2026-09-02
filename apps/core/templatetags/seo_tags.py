"""Balises de référencement pour les gabarits du site vitrine.

Les gabarits construisaient eux-mêmes leurs URL canoniques et leur JSON-LD, avec
un résultat différent d'une page à l'autre. Les balises ci-dessous lisent le
contexte déjà présent (``settings``, ``sites``) et rendent partout la même
sortie, sans requête supplémentaire.
"""

from django import template
from django.templatetags.static import static
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe

from apps.core import seo

register = template.Library()


# Fil d'Ariane par vue : (libellé, nom d'URL du parent).
# Le libellé de la page courante est repris de l'objet affiché quand il existe.
_TRAIL = {
    'home': [],
    'news_list': [("Actualités", 'public:news_list')],
    'news_detail': [("Actualités", 'public:news_list')],
    'events_list': [("Événements", 'public:events_list')],
    'event_detail': [("Événements", 'public:events_list')],
    'sites': [("Nos églises", 'public:sites')],
    'map': [("Nos églises", 'public:sites'), ("Carte", 'public:map')],
    'contact': [("Contact", 'public:contact')],
    'register': [("Inscription", 'public:register')],
    'donation': [("Faire un don", 'public:donation')],
    'page': [],
}

# Objet du contexte qui porte le titre de la page de détail.
_DETAIL_OBJECTS = ('article', 'event', 'page')


def _request(context):
    return context.get('request')


def _logo_url(context, request):
    """Logo absolu : celui des paramètres s'il existe, sinon celui du thème."""
    site_settings = context.get('settings')
    logo = getattr(site_settings, 'logo', None)
    if logo:
        try:
            return seo.absolute_url(request, logo.url)
        except ValueError:
            pass
    return seo.absolute_url(request, static('images/eebc-logo.png'))


@register.simple_tag(takes_context=True)
def canonical_url(context):
    request = _request(context)
    if request is None:
        return ""
    return seo.canonical_url(request)


@register.simple_tag(takes_context=True)
def seo_image(context):
    """Image de partage absolue, avec repli sur le logo."""
    request = _request(context)
    if request is None:
        return ""
    return _logo_url(context, request)


@register.simple_tag(takes_context=True)
def organization_jsonld(context):
    """Graphe église + site web + lieux de culte."""
    request = _request(context)
    if request is None:
        return ""
    payload = seo.organization_graph(
        request,
        context.get('settings'),
        context.get('sites') or [],
        _logo_url(context, request),
    )
    return mark_safe(seo.dumps(payload))


@register.simple_tag(takes_context=True)
def article_jsonld(context, article):
    """Donnees structurees d'un article d'actualite."""
    request = _request(context)
    if request is None or article is None:
        return ""
    payload = seo.article_graph(
        request, article, context.get('settings'), _logo_url(context, request)
    )
    return mark_safe(seo.dumps(payload))


@register.simple_tag(takes_context=True)
def event_jsonld(context, event):
    """Donnees structurees d'un evenement public."""
    request = _request(context)
    if request is None or event is None:
        return ""
    payload = seo.event_graph(
        request, event, context.get('settings'), _logo_url(context, request)
    )
    return mark_safe(seo.dumps(payload))


@register.simple_tag(takes_context=True)
def breadcrumb_jsonld(context):
    """Fil d'Ariane déduit de la vue courante.

    Renvoie une chaîne vide sur l'accueil : un fil d'Ariane à un seul maillon
    n'est pas éligible à l'affichage dans les résultats.
    """
    request = _request(context)
    if request is None or not getattr(request, 'resolver_match', None):
        return ""

    url_name = request.resolver_match.url_name
    if url_name not in _TRAIL:
        return ""

    trail = [("Accueil", _reverse('public:home'))]
    for label, name in _TRAIL[url_name]:
        trail.append((label, _reverse(name)))

    current = _current_title(context)
    if current:
        trail.append((current, request.path))
    if len(trail) < 2:
        return ""

    payload = seo.breadcrumb_graph(request, trail)
    return mark_safe(seo.dumps(payload))


def _current_title(context):
    for key in _DETAIL_OBJECTS:
        obj = context.get(key)
        if obj is not None and getattr(obj, 'title', None):
            return obj.title
    return ""


def _reverse(name):
    try:
        return reverse(name)
    except NoReverseMatch:
        return ""


@register.simple_tag(takes_context=True)
def geo_meta(context):
    """Balises de géolocalisation, tirées du premier site géocodé."""
    coords = seo.geo_tags(context.get('sites') or [])
    tags = [
        f'<meta name="geo.region" content="{seo.COUNTRY_CODE}">',
        f'<meta name="geo.placename" content="{coords["placename"]}">',
    ]
    if coords['position']:
        tags.append(f'<meta name="geo.position" content="{coords["position"]}">')
        tags.append(f'<meta name="ICBM" content="{coords["icbm"]}">')
    return mark_safe("\n    ".join(tags))


@register.simple_tag
def seo_default_description():
    return seo.DEFAULT_META_DESCRIPTION
