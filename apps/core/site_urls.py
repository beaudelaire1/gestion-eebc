"""
URLs pour la gestion des Sites paroissiaux (CRUD interne).
Montées sous /app/sites/
"""

from django.urls import path
from apps.core.views.sites import (
    site_list, site_detail, site_create, site_edit, site_delete, site_toggle_active
)

app_name = 'core'

urlpatterns = [
    path('', site_list, name='site_list'),
    path('create/', site_create, name='site_create'),
    path('<int:pk>/', site_detail, name='site_detail'),
    path('<int:pk>/edit/', site_edit, name='site_edit'),
    path('<int:pk>/delete/', site_delete, name='site_delete'),
    path('<int:pk>/toggle/', site_toggle_active, name='site_toggle_active'),
]
