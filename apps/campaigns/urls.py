from django.urls import path
from . import views

app_name = 'campaigns'

urlpatterns = [
    path('', views.campaign_list, name='list'),
    path('create/', views.campaign_create, name='create'),
    path('<int:pk>/', views.campaign_detail, name='detail'),
    path('<int:pk>/edit/', views.campaign_update, name='update'),
    path('<int:pk>/donate/', views.campaign_donate, name='donate'),
    path('donate/', views.campaign_donate, name='donate_general'),
    path('<int:pk>/progress/', views.campaign_progress_api, name='progress_api'),
]

