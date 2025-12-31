from django.urls import path
from . import views

app_name = 'bibleclub'

urlpatterns = [
    path('', views.bibleclub_home, name='home'),
    
    # Classes
    path('classes/', views.class_list, name='class_list'),
    path('classes/<int:pk>/', views.class_detail, name='class_detail'),
    
    # Enfants
    path('children/', views.children_list, name='children_list'),
    path('children/<int:pk>/', views.child_detail, name='child_detail'),
    
    # Sessions
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/create/', views.create_session, name='create_session'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    
    # Appel
    path('sessions/<int:session_pk>/attendance/<int:class_pk>/', views.take_attendance, name='take_attendance'),
    path('attendance/<int:attendance_pk>/update/', views.update_attendance_status, name='update_attendance'),
    
    # Transport
    path('sessions/<int:session_pk>/transport/', views.transport_checkin, name='transport_checkin'),
]

