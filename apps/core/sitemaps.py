"""Sitemaps du site public.

Le plan de site est la seule liste exhaustive dont dispose Google : une page
absente n'est découverte que si un lien interne y mène, et une page listée sans
``lastmod`` est réexplorée au rythme du robot, pas à celui des publications.

``protocol = 'https'`` est imposé partout : les URL du plan doivent correspondre
à celles des balises canoniques, sinon chaque contenu existe en double aux yeux
de l'index.
"""
from datetime import date, timedelta
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q

from .models import NewsArticle, PublicEvent, PageContent, Site


def _visible_articles():
    """Articles réellement affichés au public.

    Mêmes filtres que la vue : un plan de site qui annonce des pages en 404
    fait chuter la confiance accordée au domaine.
    """
    today = date.today()
    return NewsArticle.objects.filter(
        is_published=True,
        publish_date__lte=timezone.now(),
    ).filter(
        Q(display_start_date__isnull=True) | Q(display_start_date__lte=today)
    ).filter(
        Q(display_end_date__isnull=True) | Q(display_end_date__gte=today)
    )


class StaticViewSitemap(Sitemap):
    """Pages fixes du site vitrine.

    Les priorités sont hiérarchisées : l'accueil et « nos églises » portent la
    requête locale, les pages transactionnelles passent après.
    """
    protocol = 'https'

    # Priorité et fréquence par vue : une page de dons n'a pas à concurrencer
    # l'accueil dans l'ordre d'exploration.
    _ROUTES = {
        'public:home': (1.0, 'daily'),
        'public:sites': (0.9, 'monthly'),
        'public:map': (0.7, 'monthly'),
        'public:events_list': (0.8, 'daily'),
        'public:news_list': (0.8, 'daily'),
        'public:contact': (0.7, 'monthly'),
        'public:register': (0.6, 'monthly'),
        'public:donation': (0.5, 'monthly'),
    }

    def items(self):
        return list(self._ROUTES)

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self._ROUTES[item][0]

    def changefreq(self, item):
        return self._ROUTES[item][1]

    def lastmod(self, item):
        """Date du contenu le plus récent rattaché à la page.

        Une date figée pousse Google à espacer les visites ; une date qui bouge
        quand un article paraît fait revenir le robot le lendemain.
        """
        if item in ('public:home', 'public:news_list'):
            latest = _visible_articles().order_by('-publish_date').first()
            return latest.publish_date if latest else None
        if item == 'public:events_list':
            latest = PublicEvent.objects.filter(is_published=True).order_by(
                '-updated_at'
            ).first()
            return latest.updated_at if latest else None
        if item in ('public:sites', 'public:map'):
            latest = Site.objects.filter(is_active=True).order_by('-id').first()
            return getattr(latest, 'updated_at', None)
        return None


class NewsSitemap(Sitemap):
    """Articles d'actualité."""
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.7
    limit = 500

    def items(self):
        return _visible_articles().order_by('-publish_date')

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', None) or obj.publish_date

    def location(self, obj):
        return reverse('public:news_detail', kwargs={'slug': obj.slug})


class EventSitemap(Sitemap):
    """Événements publics.

    Les événements passés restent listés un an : ils accumulent des liens et
    répondent encore aux recherches sur l'édition précédente d'un rendez-vous.
    """
    protocol = 'https'
    changefreq = 'weekly'
    limit = 500

    def items(self):
        horizon = timezone.now().date() - timedelta(days=365)
        return PublicEvent.objects.filter(
            is_published=True,
            start_date__gte=horizon,
        ).order_by('-start_date')

    def priority(self, obj):
        # Un événement à venir mérite d'être exploré avant un événement passé.
        return 0.7 if obj.start_date >= timezone.now().date() else 0.4

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', None)

    def location(self, obj):
        return reverse('public:event_detail', kwargs={'slug': obj.slug})


class PageSitemap(Sitemap):
    """Pages de contenu éditées depuis le CMS."""
    protocol = 'https'
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return PageContent.objects.filter(is_published=True)

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', None)

    def location(self, obj):
        return reverse('public:page', kwargs={'slug': obj.slug})


sitemaps = {
    'static': StaticViewSitemap,
    'news': NewsSitemap,
    'events': EventSitemap,
    'pages': PageSitemap,
}
