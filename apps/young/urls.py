from django.urls import path
from . import views

app_name = 'young'

urlpatterns = [
    path('', views.young_home, name='home'),

    # Jeunes — CRUD complet
    path('members/', views.young_member_list, name='member_list'),
    path('members/create/', views.young_member_create, name='member_create'),
    path('members/<int:pk>/', views.young_member_detail, name='member_detail'),
    path('members/<int:pk>/edit/', views.young_member_edit, name='member_edit'),
    path('members/<int:pk>/delete/', views.young_member_delete, name='member_delete'),
    path('members/<int:pk>/print/', views.young_member_print_registration, name='member_print_registration'),

    # Groupes
    path('groups/', views.group_list, name='group_list'),
    path('groups/create/', views.group_create, name='group_create'),
    path('groups/<int:pk>/edit/', views.group_edit, name='group_edit'),
    path('groups/<int:pk>/delete/', views.group_delete, name='group_delete'),

    # Activités
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:pk>/edit/', views.event_edit, name='event_edit'),

    # Présences
    path('events/<int:event_pk>/attendance/', views.take_attendance, name='take_attendance'),
    path('attendance/<int:attendance_pk>/update/', views.update_attendance_status, name='update_attendance'),
]
