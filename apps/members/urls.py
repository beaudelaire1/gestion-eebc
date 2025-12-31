from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    path('', views.member_list, name='list'),
    path('<int:pk>/', views.member_detail, name='detail'),
]

