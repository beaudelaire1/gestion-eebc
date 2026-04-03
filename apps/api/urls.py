"""
API URL Configuration for EEBC Mobile App.

All API endpoints are prefixed with /api/v1/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from .auth_views import (
    CustomTokenObtainPairView,
    LogoutView,
    ChangePasswordView,
)

app_name = 'api'

# Router for ViewSets
router = DefaultRouter()
router.register(r'members', views.MemberViewSet, basename='member')
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'worship/services', views.WorshipServiceViewSet, basename='worship-service')
router.register(r'announcements', views.AnnouncementViewSet, basename='announcement')
router.register(r'donations', views.DonationViewSet, basename='donation')
router.register(r'public/sites', views.PublicSiteViewSet, basename='public-site')
router.register(r'public/news', views.PublicNewsViewSet, basename='public-news')
router.register(r'public/events', views.PublicEventViewSet, basename='public-event')
router.register(r'public/worship-schedules', views.PublicWorshipScheduleViewSet, basename='public-worship-schedule')

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Profile endpoint
    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    # Notifications endpoint
    path('notifications/register/', views.RegisterDeviceView.as_view(), name='register_device'),
    
    # Event registration
    path('events/<int:pk>/register/', views.EventRegistrationView.as_view(), name='event_register'),
    
    # Worship confirmation
    path('worship/confirm/', views.WorshipConfirmationView.as_view(), name='worship_confirm'),
    
    # BibleClub - For parents to see children's attendance
    path('bibleclub/my-children/', views.BibleClubMyChildrenView.as_view(), name='bibleclub_my_children'),

    # Public website endpoints
    path('public/settings/', views.PublicSettingsView.as_view(), name='public_settings'),
    path('public/meta/', views.PublicMetaView.as_view(), name='public_meta'),
    path('public/contact/', views.PublicContactView.as_view(), name='public_contact'),
    path('public/interest/', views.PublicInterestView.as_view(), name='public_interest'),
    
    # Router URLs
    path('', include(router.urls)),
]

