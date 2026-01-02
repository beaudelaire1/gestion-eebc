from django.urls import path
from . import views

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
]
