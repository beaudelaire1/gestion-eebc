from django.urls import path
from . import views

app_name = 'departments'

urlpatterns = [
    path('', views.department_list, name='list'),
    path('create/', views.department_create, name='create'),
    path('<int:pk>/', views.department_detail, name='detail'),
    path('<int:pk>/edit/', views.department_update, name='update'),
    path('<int:pk>/delete/', views.department_delete, name='delete'),
    path('<int:pk>/members/', views.department_members, name='members'),
]

