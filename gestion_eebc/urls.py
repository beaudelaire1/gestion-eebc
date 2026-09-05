"""
URL configuration for Gestion EEBC project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

from apps.communication.views import whatsapp_webhook
from apps.core.sitemaps import sitemaps
from apps.finance import views as views_finance
from apps.members.admin_views import members_map_data, members_map_view
from apps.worship.confirmation_views import confirm_role, decline_role

urlpatterns = [
    # Compatibilité avec les emails envoyés avant le montage des comptes sous /app/.
    # query_string conserve le token personnel lors de la redirection.
    path(
        'accounts/first-login-password-change/',
        RedirectView.as_view(
            pattern_name='accounts:first_login_password_change',
            permanent=False,
            query_string=True,
        ),
        name='legacy_first_login_password_change',
    ),
    path(
        'accounts/login/',
        RedirectView.as_view(
            pattern_name='accounts:login',
            permanent=False,
            query_string=True,
        ),
        name='legacy_accounts_login',
    ),

    # SEO
    path(
        'sitemap.xml',
        sitemap,
        {'sitemaps': sitemaps},
        name='django.contrib.sitemaps.views.sitemap',
    ),
    path(
        'robots.txt',
        TemplateView.as_view(template_name='robots.txt', content_type='text/plain'),
        name='robots_txt',
    ),

    # Site vitrine public
    path('', include('apps.core.urls')),

    # Health checks
    path('health/', include('apps.core.health_urls')),
    path('healthz/', include('apps.core.health_urls', namespace='core_healthz')),

    # API REST
    path('api/v1/', include('apps.api.urls')),

    # Webhook WhatsApp Meta
    path('webhooks/whatsapp/', whatsapp_webhook, name='whatsapp_webhook'),

    # Confirmation des rôles (publique)
    path('worship/confirm/<uuid:token>/', confirm_role, name='public_confirm_role'),
    path('worship/decline/<uuid:token>/', decline_role, name='public_decline_role'),

    # Vues admin personnalisées
    path('gestion-eebc/members/map/', members_map_view, name='admin_members_map'),
    path('gestion-eebc/members/map/data/', members_map_data, name='admin_members_map_data'),

    # Administration Django
    path('gestion-eebc/', admin.site.urls),

    # Application interne
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
    path('app/comparison/', views_finance.yearly_comparison, name='app_yearly_comparison'),
    path('app/worship/', include('apps.worship.urls')),
    path('app/cms/', include('apps.public.urls')),
    path('app/imports/', include('apps.imports.urls')),
    path('app/young/', include('apps.young.urls')),
    path('app/documents/', include('apps.documents.urls')),
    path('app/sites/', include('apps.core.site_urls')),

    # Exports et impressions
    path('app/exports/', include('apps.core.export_urls')),
]

# django.conf.urls.static.static() is development-only. In production,
# the configured storage backend (Cloudinary) owns media URLs and delivery.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # The toolbar URLs import its models, so the app must actually be
    # installed. Test settings run with DEBUG toggled on but without
    # debug_toolbar in INSTALLED_APPS.
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns = [
            path('__debug__/', include('debug_toolbar.urls')),
        ] + urlpatterns

admin.site.site_header = "Gestion EEBC"
admin.site.site_title = "EEBC Admin"
admin.site.index_title = "Tableau de bord administrateur"

handler403 = 'gestion_eebc.error_views.handler403'
handler404 = 'gestion_eebc.error_views.handler404'
handler500 = 'gestion_eebc.error_views.handler500'
