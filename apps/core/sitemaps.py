"""
Sitemaps pour le référencement SEO du site public EEBC.
"""
from datetime import date
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q

from .models import NewsArticle, PublicEvent, PageContent, Site


class StaticViewSitemap(Sitemap):
    """Sitemap des pages statiques publiques."""
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return [
            'public:home',
            'public:news_list',
            'public:events_list',
            'public:contact',
            'public:register',
            'public:sites',
            'public:donation',
        ]

    def location(self, item):
        return reverse(item)


class NewsSitemap(Sitemap):
    """Sitemap des articles d'actualité."""
    changefreq = 'daily'
    priority = 0.7

    def items(self):
        today = date.today()
        now = timezone.now()
        return NewsArticle.objects.filter(
            is_published=True,
            publish_date__lte=now,
        ).filter(
            Q(display_start_date__isnull=True) | Q(display_start_date__lte=today)
        ).filter(
            Q(display_end_date__isnull=True) | Q(display_end_date__gte=today)
        ).order_by('-publish_date')

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', obj.publish_date)

    def location(self, obj):
        return reverse('public:news_detail', kwargs={'slug': obj.slug})


class EventSitemap(Sitemap):
    """Sitemap des événements publics."""
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return PublicEvent.objects.filter(
            is_published=True,
            start_date__gte=timezone.now().date(),
        ).order_by('start_date')

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', None)

    def location(self, obj):
        return reverse('public:event_detail', kwargs={'slug': obj.slug})


class PageSitemap(Sitemap):
    """Sitemap des pages de contenu."""
    changefreq = 'monthly'
    priority = 0.5

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
