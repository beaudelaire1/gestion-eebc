from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    # Membres
    path('', views.member_list, name='list'),
    path('<int:pk>/', views.member_detail, name='detail'),
    
    # Événements de vie (Pastoral CRM)
    path('life-events/', views.life_event_list, name='life_events'),
    path('life-events/create/', views.life_event_create, name='life_event_create'),
    path('life-events/<int:pk>/', views.life_event_detail, name='life_event_detail'),
    path('life-events/<int:pk>/mark-visited/', views.life_event_mark_visited, name='life_event_mark_visited'),
    path('life-events/<int:pk>/mark-announced/', views.life_event_mark_announced, name='life_event_mark_announced'),
    
    # Visites pastorales
    path('visits/', views.visit_list, name='visits'),
    path('visits/create/', views.visit_create, name='visit_create'),
    path('visits/<int:pk>/', views.visit_detail, name='visit_detail'),
    path('visits/<int:pk>/complete/', views.visit_complete, name='visit_complete'),
    path('visits/needed/', views.members_needing_visit, name='members_needing_visit'),
]

