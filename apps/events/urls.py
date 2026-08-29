from django.urls import path
from . import views
from . import security_views as sv

app_name = 'events'

urlpatterns = [
    path('', sv.event_list, name='list'),
    path('advanced/', sv.event_list_advanced, name='list_advanced'),
    path('calendar/', sv.calendar_view, name='calendar'),
    path('calendar/print/', sv.calendar_print, name='calendar_print'),
    path('calendar/pdf/', sv.calendar_pdf, name='calendar_pdf'),
    path('api/events/', sv.events_json, name='events_json'),
    path('create/', views.event_create, name='create'),
    path('<int:pk>/', sv.event_detail, name='detail'),
    path('<int:pk>/edit/', views.event_update, name='update'),
    path('<int:pk>/cancel/', views.event_cancel, name='cancel'),
    path('<int:pk>/duplicate/', sv.event_duplicate, name='duplicate'),
    path('upcoming/', sv.upcoming_events_partial, name='upcoming'),

    # Catégories d'événements
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
]
