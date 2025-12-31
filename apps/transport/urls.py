from django.urls import path
from . import views

app_name = 'transport'

urlpatterns = [
    path('drivers/', views.driver_list, name='drivers'),
    path('requests/', views.transport_requests, name='requests'),
]

