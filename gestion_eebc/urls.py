"""
URL configuration for Gestion EEBC project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Import des vues admin personnalisées
from apps.members.admin_views import members_map_view, members_map_data
# Import des vues de confirmation publiques
from apps.worship.confirmation_views import confirm_role, decline_role

urlpatterns = [
    # Site vitrine public (page d'accueil par défaut)
    path('', include('apps.core.urls')),
    
    # Confirmation des rôles (accessible sans connexion)
    path('worship/confirm/<uuid:token>/', confirm_role, name='public_confirm_role'),
    path('worship/decline/<uuid:token>/', decline_role, name='public_decline_role'),
    
    # Vues admin personnalisées (avant admin/)
    path('admin/members/map/', members_map_view, name='admin_members_map'),
    path('admin/members/map/data/', members_map_data, name='admin_members_map_data'),
    
    # Administration Django
    path('admin/', admin.site.urls),
    
    # Application interne (après connexion)
    path('app/', include('apps.dashboard.urls')),
    path('app/accounts/', include('apps.accounts.urls')),
    path('app/members/', include('apps.members.urls')),
    path('app/departments/', include('apps.departments.urls')),
    path('app/transport/', include('apps.transport.urls')),
    path('app/inventory/', include('apps.inventory.urls')),
    path('app/campaigns/', include('apps.campaigns.urls')),
    path('app/bibleclub/', include('apps.bibleclub.urls')),
    path('app/events/', include('apps.events.urls')),
    path('app/groups/', include('apps.groups.urls')),
    path('app/communication/', include('apps.communication.urls')),
    path('app/finance/', include('apps.finance.urls')),
    path('app/worship/', include('apps.worship.urls')),
    
    # Exports et impressions
    path('app/exports/', include('apps.core.export_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "Gestion EEBC"
admin.site.site_title = "EEBC Admin"
admin.site.index_title = "Tableau de bord administrateur"

# Configuration des handlers d'erreurs personnalisés
from .error_views import handler403, handler404, handler500

# Handlers d'erreurs (actifs uniquement en production, DEBUG=False)
handler403 = 'gestion_eebc.error_views.handler403'
handler404 = 'gestion_eebc.error_views.handler404'
handler500 = 'gestion_eebc.error_views.handler500'

