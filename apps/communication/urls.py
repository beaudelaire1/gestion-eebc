from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/<int:pk>/', views.notification_detail, name='notification_detail'),
    path('notifications/count/', views.notifications_count, name='notifications_count'),
    path('announcements/', views.announcements_list, name='announcements'),
]

