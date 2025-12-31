from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    path('', views.group_list, name='list'),
    path('<int:pk>/', views.group_detail, name='detail'),
]

