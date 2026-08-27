from django.contrib.auth.decorators import login_required
from django.urls import path

from apps.core.permissions import module_required, role_required
from . import admin_views, family_views, kanban_views, views

app_name = 'members'


def member_read_access(view):
    """Authentifie puis vérifie l'accès interne au module membres."""
    return login_required(module_required('members')(view))


def member_write_access(view):
    """Réserve les mutations de l'annuaire à admin et secrétariat."""
    return login_required(role_required('admin', 'secretariat')(view))


urlpatterns = [
    # Membres
    path('', member_read_access(views.member_list), name='list'),
    path('create/', member_write_access(views.member_create), name='create'),
    path('<int:pk>/', member_read_access(views.member_detail), name='detail'),
    path('<int:pk>/edit/', member_write_access(views.member_edit), name='edit'),
    path('<int:pk>/delete/', member_write_access(views.member_delete), name='delete'),
    path('<int:pk>/print/', member_read_access(views.member_print_registration), name='print_registration'),

    # Carte des membres - les vues conservent leur restriction admin/secretariat
    path('map/', admin_views.members_map_view, name='map'),
    path('map/data/', admin_views.members_map_data, name='map_data'),

    # Familles - ces écrans exposent également des données de membres
    path('families/', member_read_access(family_views.family_list), name='family_list'),
    path('families/create/', member_write_access(family_views.family_create), name='family_create'),
    path('families/<int:pk>/', member_read_access(family_views.family_detail), name='family_detail'),
    path('families/<int:pk>/edit/', member_write_access(family_views.family_edit), name='family_edit'),
    path('families/<int:pk>/add-member/', member_write_access(family_views.family_add_member), name='family_add_member'),
    path('api/member/<int:pk>/data/', member_read_access(family_views.member_api_data), name='member_api_data'),

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
