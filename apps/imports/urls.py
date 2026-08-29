from django.urls import path
from . import views
from . import security_views as sv

app_name = 'imports'

urlpatterns = [
    # Hub central
    path('', views.export_hub, name='hub'),

    # Imports traditionnels
    path('imports/', views.import_list, name='list'),
    path('imports/create/', sv.import_create, name='create'),
    path('imports/<int:pk>/', views.import_detail, name='detail'),
    path('imports/<int:pk>/status/', views.import_status, name='status'),
    path('imports/<int:pk>/delete/', sv.import_delete, name='delete'),
    path('imports/bulk-delete/', sv.import_bulk_delete, name='bulk_delete'),
    path('template/<str:import_type>/', views.download_template, name='template'),

    # Exports sensibles
    path('export/members/', sv.export_members, name='export_members'),
    path('export/children/', sv.export_children, name='export_children'),
    path('export/young-members/', sv.export_young_members, name='export_young_members'),
    path('export/groups/', sv.export_groups, name='export_groups'),
    path('export/inventory/', sv.export_inventory, name='export_inventory'),
    path('export/transport/', sv.export_transport, name='export_transport'),
    path('export/communication/', sv.export_communication, name='export_communication'),
]
