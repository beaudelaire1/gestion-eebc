"""
URL configuration for Gestion EEBC project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.dashboard.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('members/', include('apps.members.urls')),
    path('departments/', include('apps.departments.urls')),
    path('transport/', include('apps.transport.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('campaigns/', include('apps.campaigns.urls')),
    path('bibleclub/', include('apps.bibleclub.urls')),
    path('events/', include('apps.events.urls')),
    path('groups/', include('apps.groups.urls')),
    path('communication/', include('apps.communication.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "Gestion EEBC"
admin.site.site_title = "EEBC Admin"
admin.site.index_title = "Tableau de bord administrateur"

