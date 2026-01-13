from django.urls import path
from . import views

app_name = 'bibleclub'

urlpatterns = [
    path('', views.bibleclub_home, name='home'),
    path('chart-data/', views.attendance_chart_data, name='attendance_chart_data'),
    
    # Classes - CRUD complet
    path('classes/', views.class_list, name='class_list'),
    path('classes/create/', views.bible_class_create, name='bible_class_create'),
    path('classes/<int:pk>/', views.class_detail, name='class_detail'),
    path('classes/<int:pk>/edit/', views.bible_class_update, name='bible_class_update'),
    path('classes/<int:pk>/delete/', views.bible_class_delete, name='bible_class_delete'),
    
    # Moniteurs - CRUD complet
    path('monitors/', views.monitor_list, name='monitor_list'),
    path('monitors/create/', views.monitor_create, name='monitor_create'),
    path('monitors/<int:pk>/edit/', views.monitor_update, name='monitor_update'),
    path('monitors/<int:pk>/delete/', views.monitor_delete, name='monitor_delete'),
    
    # Enfants
    path('children/', views.children_list, name='children_list'),
    path('children/create/', views.child_create, name='child_create'),
    path('children/<int:pk>/', views.child_detail, name='child_detail'),
    path('children/<int:pk>/edit/', views.child_edit, name='child_edit'),
    path('children/<int:pk>/delete/', views.child_delete, name='child_delete'),
    
    # Sessions
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/create/', views.create_session, name='create_session'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    
    # Appel
    path('sessions/<int:session_pk>/attendance/<int:class_pk>/', views.take_attendance, name='take_attendance'),
    path('attendance/<int:attendance_pk>/update/', views.update_attendance_status, name='update_attendance'),
    
    # Transport
    path('sessions/<int:session_pk>/transport/', views.transport_checkin, name='transport_checkin'),
    
    # API HTMX
    path('api/my-class-children/', views.my_class_children, name='my_class_children'),
]

