from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='list'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('calendar/print/', views.calendar_print, name='calendar_print'),
    path('calendar/pdf/', views.calendar_pdf, name='calendar_pdf'),
    path('api/events/', views.events_json, name='events_json'),
    path('<int:pk>/', views.event_detail, name='detail'),
    path('upcoming/', views.upcoming_events_partial, name='upcoming'),
]
