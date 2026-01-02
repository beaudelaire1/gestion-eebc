from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    # Notifications
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/<int:pk>/', views.notification_detail, name='notification_detail'),
    path('notifications/<int:pk>/mark-read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', views.notifications_mark_all_read, name='notifications_mark_all_read'),
    path('notifications/count/', views.notifications_count, name='notifications_count'),
    
    # Annonces
    path('announcements/', views.announcements_list, name='announcements'),
    path('announcements/create/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/', views.announcement_detail, name='announcement_detail'),
    
    # Logs
    path('logs/email/', views.email_logs, name='email_logs'),
    path('logs/sms/', views.sms_logs, name='sms_logs'),
]

