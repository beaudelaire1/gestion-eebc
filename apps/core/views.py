"""
Vues du site vitrine public.
"""
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from .models import (
    Site, PageContent, NewsArticle, ContactMessage, 
    VisitorRegistration, PublicEvent, Slider, SiteSettings
)


def get_visible_articles_queryset():
    """
    Retourne un queryset des articles visibles publiquement.
    Prend en compte : is_published, publish_date, display_start_date, display_end_date
    """
    today = date.today()
    now = timezone.now()
    
    return NewsArticle.objects.filter(
        is_published=True,
        publish_date__lte=now
    ).filter(
        Q(display_start_date__isnull=True) | Q(display_start_date__lte=today)
    ).filter(
        Q(display_end_date__isnull=True) | Q(display_end_date__gte=today)
    )


class PublicMixin:
    """Mixin pour ajouter les données communes aux vues publiques."""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = SiteSettings.get_settings()
        context['sites'] = Site.objects.filter(is_active=True)
        context['menu_pages'] = PageContent.objects.filter(
            is_published=True, 
            show_in_menu=True
        ).order_by('menu_order')
        return context


class HomeView(PublicMixin, TemplateView):
    """Page d'accueil du site vitrine."""
    template_name = 'public/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Slides du carrousel
        context['slides'] = Slider.objects.filter(is_active=True).order_by('order')
        
        # Articles à la une (visibles uniquement)
        context['featured_articles'] = get_visible_articles_queryset().order_by(
            '-is_featured', '-publish_date'
        )[:3]
        
        # Événements à venir
        context['upcoming_events'] = PublicEvent.objects.filter(
            is_published=True,
            start_date__gte=timezone.now().date()
        ).order_by('start_date')[:4]
        
        # Sites avec leurs infos
        context['church_sites'] = Site.objects.filter(is_active=True)
        
        return context


class PageDetailView(PublicMixin, DetailView):
    """Affichage d'une page statique."""
    model = PageContent
    template_name = 'public/page.html'
    context_object_name = 'page'
    slug_field = 'slug'
    
    def get_queryset(self):
        return PageContent.objects.filter(is_published=True)


class NewsListView(PublicMixin, ListView):
    """Liste des articles."""
    model = NewsArticle
    template_name = 'public/news_list.html'
    context_object_name = 'articles'
    paginate_by = 9
    
    def get_queryset(self):
        queryset = get_visible_articles_queryset().order_by('-publish_date')
        
        # Filtre par catégorie
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = NewsArticle.Category.choices
        context['current_category'] = self.request.GET.get('category', '')
        return context


class NewsDetailView(PublicMixin, DetailView):
    """Détail d'un article."""
    model = NewsArticle
    template_name = 'public/news_detail.html'
    context_object_name = 'article'
    slug_field = 'slug'
    
    def get_queryset(self):
        return get_visible_articles_queryset()
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Incrémenter le compteur de vues
        obj.views_count += 1
        obj.save(update_fields=['views_count'])
        return obj


class EventListView(PublicMixin, ListView):
    """Liste des événements publics."""
    model = PublicEvent
    template_name = 'public/events_list.html'
    context_object_name = 'events'
    paginate_by = 12
    
    def get_queryset(self):
        return PublicEvent.objects.filter(
            is_published=True,
            start_date__gte=timezone.now().date()
        ).order_by('start_date')


class EventDetailView(PublicMixin, DetailView):
    """Détail d'un événement."""
    model = PublicEvent
    template_name = 'public/event_detail.html'
    context_object_name = 'event'
    slug_field = 'slug'
    
    def get_queryset(self):
        return PublicEvent.objects.filter(is_published=True)


class ContactView(PublicMixin, CreateView):
    """Formulaire de contact."""
    model = ContactMessage
    template_name = 'public/contact.html'
    fields = ['name', 'email', 'phone', 'subject', 'message', 'site']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subjects'] = ContactMessage.Subject.choices
        return context
    
    def form_valid(self, form):
        # Enregistrer l'IP
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            form.instance.ip_address = x_forwarded_for.split(',')[0]
        else:
            form.instance.ip_address = self.request.META.get('REMOTE_ADDR')
        
        response = super().form_valid(form)
        
        # Envoyer les emails de notification
        from .emails import send_contact_notification
        try:
            send_contact_notification(self.object)
        except Exception as e:
            print(f"Erreur envoi email contact: {e}")
        
        messages.success(self.request, 'Votre message a été envoyé avec succès. Nous vous répondrons bientôt.')
        return response
    
    def get_success_url(self):
        return self.request.path


class VisitorRegistrationView(PublicMixin, CreateView):
    """Formulaire d'inscription visiteur."""
    model = VisitorRegistration
    template_name = 'public/register.html'
    fields = ['first_name', 'last_name', 'email', 'phone', 'city', 'interest', 'preferred_site', 'message']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['interests'] = VisitorRegistration.Interest.choices
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Envoyer les emails de notification
        from .emails import send_registration_notification
        try:
            send_registration_notification(self.object)
        except Exception as e:
            print(f"Erreur envoi email inscription: {e}")
        
        messages.success(self.request, 'Merci pour votre inscription ! Nous vous contacterons bientôt.')
        return response
    
    def get_success_url(self):
        return self.request.path


class SitesView(PublicMixin, TemplateView):
    """Page présentant les sites/églises."""
    template_name = 'public/sites.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['church_sites'] = Site.objects.filter(is_active=True)
        return context
