from django.urls import path
from . import views

app_name = 'campaigns'

urlpatterns = [
    path('', views.campaign_list, name='list'),
    path('<int:pk>/', views.campaign_detail, name='detail'),
]

