from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.equipment_list, name='list'),
    path('create/', views.equipment_create, name='create'),
    path('<int:pk>/', views.equipment_detail, name='detail'),
    path('<int:pk>/edit/', views.equipment_update, name='update'),
    path('<int:pk>/delete/', views.equipment_delete, name='delete'),
]

