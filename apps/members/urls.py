from django.urls import path
from . import views
from . import security_views as sv
from . import admin_views

app_name = 'members'

urlpatterns = [
    # Membres
    path('', sv.member_list, name='list'),
    path('create/', views.member_create, name='create'),
    path('<int:pk>/', sv.member_detail, name='detail'),
    path('<int:pk>/edit/', views.member_edit, name='edit'),
    path('<int:pk>/delete/', views.member_delete, name='delete'),
    path('<int:pk>/print/', sv.member_print_registration, name='print_registration'),

    # Carte des membres
    path('map/', admin_views.members_map_view, name='map'),
    path('map/data/', admin_views.members_map_data, name='map_data'),

    # Familles
    path('families/', sv.family_list, name='family_list'),
    path('families/create/', sv.family_create, name='family_create'),
    path('families/<int:pk>/', sv.family_detail, name='family_detail'),
    path('families/<int:pk>/edit/', sv.family_edit, name='family_edit'),
    path('families/<int:pk>/delete/', sv.family_delete, name='family_delete'),
    path('families/<int:pk>/add-member/', sv.family_add_member, name='family_add_member'),
    path('api/member/<int:pk>/data/', sv.member_api_data, name='member_api_data'),

    # Événements de vie (Pastoral CRM)
    path('life-events/', views.life_event_list, name='life_events'),
    path('life-events/create/', views.life_event_create, name='life_event_create'),
    path('life-events/<int:pk>/', sv.life_event_detail, name='life_event_detail'),
    path('life-events/<int:pk>/mark-visited/', sv.life_event_mark_visited, name='life_event_mark_visited'),
    path('life-events/<int:pk>/mark-announced/', sv.life_event_mark_announced, name='life_event_mark_announced'),

    # Visites pastorales
    path('visits/', sv.visit_list, name='visits'),
    path('visits/create/', views.visit_create, name='visit_create'),
    path('visits/<int:pk>/', sv.visit_detail, name='visit_detail'),
    path('visits/<int:pk>/complete/', sv.visit_complete, name='visit_complete'),
    path('visits/needed/', views.members_needing_visit, name='members_needing_visit'),

    # Tableau Kanban des visites
    path('kanban/', sv.SecureKanbanBoardView.as_view(), name='kanban'),
    path('kanban/update/', sv.SecureKanbanUpdateView.as_view(), name='kanban_update'),
    path('kanban/create/', sv.SecureQuickVisitCreateView.as_view(), name='kanban_create'),
]
