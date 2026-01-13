from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.equipment_list, name='list'),
    path('create/', views.equipment_create, name='create'),
    path('<int:pk>/', views.equipment_detail, name='detail'),
    path('<int:pk>/edit/', views.equipment_update, name='update'),
    path('<int:pk>/delete/', views.equipment_delete, name='delete'),
    
    # Catégories d'équipement
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
]

