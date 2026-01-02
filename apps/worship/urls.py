"""URLs pour le module Worship."""

from django.urls import path
from . import views
from . import confirmation_views

app_name = 'worship'

urlpatterns = [
    # Services (ancien système)
    path('', views.service_list, name='service_list'),
    path('services/<int:pk>/', views.service_detail, name='service_detail'),
    path('services/create/', views.service_create, name='service_create'),
    path('services/<int:pk>/edit/', views.service_edit, name='service_edit'),
    
    # Planification mensuelle (nouveau système)
    path('planning/', views.monthly_schedule_list, name='schedule_list'),
    path('planning/create/', views.monthly_schedule_create, name='schedule_create'),
    path('planning/<int:pk>/', views.monthly_schedule_detail, name='schedule_detail'),
    path('planning/<int:pk>/edit/', views.monthly_schedule_edit, name='schedule_edit'),
    path('planning/<int:pk>/generate/', views.generate_sundays, name='generate_sundays'),
    path('planning/<int:pk>/publish/', views.publish_schedule, name='publish_schedule'),
    path('planning/<int:pk>/send-notifications/', views.send_notifications, name='send_notifications'),
    
    # Cultes programmés
    path('culte/<int:pk>/', views.scheduled_service_detail, name='culte_detail'),
    path('culte/<int:pk>/edit/', views.scheduled_service_edit, name='culte_edit'),
    
    # Assignations de rôles avec confirmation
    path('culte/<int:service_pk>/assignments/', confirmation_views.role_assignments_list, name='role_assignments'),
    path('culte/<int:service_pk>/assignments/create/', confirmation_views.create_role_assignment, name='create_role_assignment'),
    path('culte/<int:service_pk>/assignments/send-all/', confirmation_views.send_all_notifications, name='send_all_notifications'),
    path('assignment/<int:pk>/send/', confirmation_views.send_assignment_notification, name='send_assignment_notification'),
    
    # Confirmation publique (sans connexion)
    path('confirm/<uuid:token>/', confirmation_views.confirm_role, name='confirm_role'),
    path('decline/<uuid:token>/', confirmation_views.decline_role, name='decline_role'),
    
    # Rôles (HTMX - ancien système)
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
