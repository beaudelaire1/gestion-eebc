from django.urls import path
from . import views
from apps.finance.donation_views import (
    DonationPageView, CreateDonationSessionView,
    DonationSuccessView, DonationCancelView, StripeWebhookView
)

app_name = 'public'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('actualites/', views.NewsListView.as_view(), name='news_list'),
    path('actualites/<slug:slug>/', views.NewsDetailView.as_view(), name='news_detail'),
    path('evenements/', views.EventListView.as_view(), name='events_list'),
    path('evenements/<slug:slug>/', views.EventDetailView.as_view(), name='event_detail'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('inscription/', views.VisitorRegistrationView.as_view(), name='register'),
    path('nos-eglises/', views.SitesView.as_view(), name='sites'),
    path('page/<slug:slug>/', views.PageDetailView.as_view(), name='page'),
    
    # Dons en ligne
    path('don/', DonationPageView.as_view(), name='donation'),
    path('don/creer-session/', CreateDonationSessionView.as_view(), name='donation_create_session'),
    path('don/succes/', DonationSuccessView.as_view(), name='donation_success'),
    path('don/annule/', DonationCancelView.as_view(), name='donation_cancel'),
    path('webhooks/stripe/', StripeWebhookView.as_view(), name='stripe_webhook'),
    
    # Carte interactive
    path('carte/', views.MapView.as_view(), name='map'),
    
    # Page offline (PWA)
    path('offline/', views.OfflineView.as_view(), name='offline'),
]
