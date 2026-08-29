from django.urls import path
from . import views

app_name = 'public_cms'

urlpatterns = [
    # News
    path('news/', views.NewsListView.as_view(), name='news_list'),
    path('news/create/', views.NewsCreateView.as_view(), name='news_create'),
    path('news/<int:pk>/edit/', views.NewsUpdateView.as_view(), name='news_update'),
    path('news/<int:pk>/delete/', views.NewsDeleteView.as_view(), name='news_delete'),
    
    # Pages
    path('pages/', views.PageListView.as_view(), name='page_list'),
    path('pages/create/', views.PageCreateView.as_view(), name='page_create'),
    path('pages/<int:pk>/edit/', views.PageUpdateView.as_view(), name='page_update'),
    path('pages/<int:pk>/delete/', views.PageDeleteView.as_view(), name='page_delete'),
    
    # Testimonies
    path('testimonies/', views.TestimonyListView.as_view(), name='testimony_list'),
    path('testimonies/create/', views.TestimonyCreateView.as_view(), name='testimony_create'),
    path('testimonies/<int:pk>/edit/', views.TestimonyUpdateView.as_view(), name='testimony_update'),
    path('testimonies/<int:pk>/delete/', views.TestimonyDeleteView.as_view(), name='testimony_delete'),
    
    # Worship Schedules
    path('schedules/', views.ScheduleListView.as_view(), name='schedule_list'),
    path('schedules/create/', views.ScheduleCreateView.as_view(), name='schedule_create'),
    path('schedules/<int:pk>/edit/', views.ScheduleUpdateView.as_view(), name='schedule_update'),
    path('schedules/<int:pk>/delete/', views.ScheduleDeleteView.as_view(), name='schedule_delete'),
]

urlpatterns += [
    # Public Events
    path('events/', views.PublicEventListView.as_view(), name='event_list'),
    path('events/create/', views.PublicEventCreateView.as_view(), name='event_create'),
    path('events/<int:pk>/edit/', views.PublicEventUpdateView.as_view(), name='event_update'),
    path('events/<int:pk>/delete/', views.PublicEventDeleteView.as_view(), name='event_delete'),
]
