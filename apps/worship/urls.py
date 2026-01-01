"""URLs pour le module Worship."""

from django.urls import path
from . import views

app_name = 'worship'

urlpatterns = [
    # Services
    path('', views.service_list, name='service_list'),
    path('services/<int:pk>/', views.service_detail, name='service_detail'),
    path('services/create/', views.service_create, name='service_create'),
    path('services/<int:pk>/edit/', views.service_edit, name='service_edit'),
    
    # Rôles (HTMX)
    path('services/<int:service_pk>/roles/assign/', views.role_assign, name='role_assign'),
    path('roles/<int:pk>/confirm/', views.role_confirm, name='role_confirm'),
    path('roles/<int:pk>/decline/', views.role_decline, name='role_decline'),
    
    # Programme
    path('services/<int:service_pk>/plan/', views.plan_edit, name='plan_edit'),
    path('services/<int:service_pk>/plan/add/', views.plan_item_add, name='plan_item_add'),
    
    # PDF
    path('services/<int:pk>/run-sheet/', views.run_sheet_pdf, name='run_sheet_pdf'),
    
    # Templates
    path('services/<int:service_pk>/apply-template/<int:template_pk>/', 
         views.apply_template, name='apply_template'),
]
