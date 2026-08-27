"""API URL Configuration for EEBC Mobile App.

All API endpoints are prefixed with /api/v1/.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .auth_views import LogoutView
from .mfa_auth import (
    SecureChangePasswordView,
    SecureTokenObtainPairView,
    SecureTokenRefreshView,
)

app_name = 'api'

router = DefaultRouter()
router.register(r'members', views.MemberViewSet, basename='member')
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'worship/services', views.WorshipServiceViewSet, basename='worship-service')
router.register(r'announcements', views.AnnouncementViewSet, basename='announcement')
router.register(r'donations', views.DonationViewSet, basename='donation')
router.register(r'public/sites', views.PublicSiteViewSet, basename='public-site')
router.register(r'public/news', views.PublicNewsViewSet, basename='public-news')
router.register(r'public/events', views.PublicEventViewSet, basename='public-event')
router.register(
    r'public/worship-schedules',
    views.PublicWorshipScheduleViewSet,
    basename='public-worship-schedule',
)

urlpatterns = [
    path('auth/login/', SecureTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', SecureTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/password/', SecureChangePasswordView.as_view(), name='change_password'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('notifications/register/', views.RegisterDeviceView.as_view(), name='register_device'),
    path('events/<int:pk>/register/', views.EventRegistrationView.as_view(), name='event_register'),
    path('worship/confirm/', views.WorshipConfirmationView.as_view(), name='worship_confirm'),
    path(
        'bibleclub/my-children/',
        views.BibleClubMyChildrenView.as_view(),
        name='bibleclub_my_children',
    ),
    path('transport/my-requests/', views.TransportMyRequestsView.as_view(), name='transport_my_requests'),
    path(
        'transport/requests/<int:pk>/live/status/',
        views.TransportApiLiveStatusView.as_view(),
        name='transport_api_live_status',
    ),
    path(
        'transport/requests/<int:pk>/live/update/',
        views.TransportApiLiveUpdateView.as_view(),
        name='transport_api_live_update',
    ),
    path('public/settings/', views.PublicSettingsView.as_view(), name='public_settings'),
    path('public/meta/', views.PublicMetaView.as_view(), name='public_meta'),
    path('public/contact/', views.PublicContactView.as_view(), name='public_contact'),
    path('public/interest/', views.PublicInterestView.as_view(), name='public_interest'),
    path('', include(router.urls)),
]
