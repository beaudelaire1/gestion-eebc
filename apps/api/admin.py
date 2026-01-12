"""
Admin configuration for API models.
"""
from django.contrib import admin
from .models import DeviceToken, AnnouncementReadStatus


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'device_name', 'is_active', 'updated_at']
    list_filter = ['platform', 'is_active']
    search_fields = ['user__username', 'user__email', 'device_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'token', 'platform', 'device_name')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AnnouncementReadStatus)
class AnnouncementReadStatusAdmin(admin.ModelAdmin):
    list_display = ['user', 'announcement', 'read_at']
    list_filter = ['read_at']
    search_fields = ['user__username', 'announcement__title']
    readonly_fields = ['read_at']
