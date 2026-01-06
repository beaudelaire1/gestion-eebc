from django.urls import path
from . import views
from . import kanban_views
from . import family_views
from . import admin_views

app_name = 'members'

urlpatterns = [
    # Membres
    path('', views.member_list, name='list'),
    path('create/', views.member_create, name='create'),
    path('<int:pk>/', views.member_detail, name='detail'),
    path('<int:pk>/edit/', views.member_edit, name='edit'),
    path('<int:pk>/delete/', views.member_delete, name='delete'),
    
    # Carte des membres
    path('map/', admin_views.members_map_view, name='map'),
    path('map/data/', admin_views.members_map_data, name='map_data'),
    
    # Familles
    path('families/', family_views.family_list, name='family_list'),
    path('families/create/', family_views.family_create, name='family_create'),
    path('families/<int:pk>/', family_views.family_detail, name='family_detail'),
    path('families/<int:pk>/edit/', family_views.family_edit, name='family_edit'),
    path('families/<int:pk>/add-member/', family_views.family_add_member, name='family_add_member'),
    
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
    
    # Tableau Kanban des visites
    path('kanban/', kanban_views.KanbanBoardView.as_view(), name='kanban'),
    path('kanban/update/', kanban_views.KanbanUpdateView.as_view(), name='kanban_update'),
    path('kanban/create/', kanban_views.QuickVisitCreateView.as_view(), name='kanban_create'),
]

