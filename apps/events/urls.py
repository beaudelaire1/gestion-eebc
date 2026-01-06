from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='list'),
    path('advanced/', views.event_list_advanced, name='list_advanced'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('calendar/print/', views.calendar_print, name='calendar_print'),
    path('calendar/pdf/', views.calendar_pdf, name='calendar_pdf'),
    path('api/events/', views.events_json, name='events_json'),
    path('create/', views.event_create, name='create'),
    path('<int:pk>/', views.event_detail, name='detail'),
    path('<int:pk>/edit/', views.event_update, name='update'),
    path('<int:pk>/cancel/', views.event_cancel, name='cancel'),
    path('<int:pk>/duplicate/', views.event_duplicate, name='duplicate'),
    path('upcoming/', views.upcoming_events_partial, name='upcoming'),
]
