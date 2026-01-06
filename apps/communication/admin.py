from django.contrib import admin
from django import forms
from .models import Notification, EmailLog, SMSLog, Announcement
from apps.core.widgets import TinyMCEWidget


class AnnouncementAdminForm(forms.ModelForm):
    """Formulaire admin avec TinyMCE pour les annonces."""
    class Meta:
        model = Announcement
        fields = '__all__'
        widgets = {
            'content': TinyMCEWidget(config={'height': 300}),
        }


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'recipient__username']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'read_at']


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['subject', 'recipient_email', 'status', 'sent_at', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['subject', 'recipient_email', 'recipient_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'sent_at']


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['recipient_phone', 'recipient_name', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['recipient_phone', 'recipient_name', 'message']
    date_hierarchy = 'created_at'


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    form = AnnouncementAdminForm
    list_display = ['title', 'author', 'is_active', 'is_pinned', 'start_date', 'end_date']
    list_filter = ['is_active', 'is_pinned']
    search_fields = ['title', 'content']
    date_hierarchy = 'created_at'
    
    class Media:
        js = ('https://cdn.tiny.cloud/1/6qr0im1d33wizm1ytimh1kpwbugqeb8r4fq1gebb03rme6hv/tinymce/6/tinymce.min.js',)

