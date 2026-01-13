from django.urls import path
from . import views

app_name = 'transport'

urlpatterns = [
    # Driver URLs
    path('drivers/', views.driver_list, name='drivers'),
    path('drivers/create/', views.driver_create, name='driver_create'),
    path('drivers/<int:pk>/', views.driver_detail, name='driver_detail'),
    path('drivers/<int:pk>/edit/', views.driver_update, name='driver_update'),
    path('drivers/<int:pk>/delete/', views.driver_delete, name='driver_delete'),
    
    # Transport Request URLs
    path('requests/', views.transport_requests, name='requests'),
    path('requests/create/', views.transport_request_create, name='request_create'),
    path('requests/<int:pk>/', views.transport_request_detail, name='request_detail'),
    path('requests/<int:pk>/edit/', views.transport_request_update, name='request_update'),
    path('requests/<int:pk>/delete/', views.transport_request_delete, name='request_delete'),
    path('requests/<int:pk>/assign/', views.assign_driver, name='assign_driver'),
    
    # Calendar URLs
    path('calendar/', views.transport_calendar, name='calendar'),
    path('calendar/data/', views.transport_calendar_data, name='calendar_data'),
]

