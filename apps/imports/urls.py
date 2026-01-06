from django.urls import path
from . import views

app_name = 'imports'

urlpatterns = [
    # Hub central
    path('', views.export_hub, name='hub'),
    
    # Imports traditionnels
    path('imports/', views.import_list, name='list'),
    path('imports/create/', views.import_create, name='create'),
    path('imports/<int:pk>/', views.import_detail, name='detail'),
    path('imports/<int:pk>/status/', views.import_status, name='status'),
    path('template/<str:import_type>/', views.download_template, name='template'),
    
    # Exports existants (membres & enfants)
    path('export/members/', views.export_members, name='export_members'),
    path('export/children/', views.export_children, name='export_children'),
    
    # Nouveaux exports
    path('export/groups/', views.export_groups, name='export_groups'),
    path('export/inventory/', views.export_inventory, name='export_inventory'),
    path('export/transport/', views.export_transport, name='export_transport'),
    path('export/communication/', views.export_communication, name='export_communication'),
]