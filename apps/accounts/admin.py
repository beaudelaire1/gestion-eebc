from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']
    list_filter = ['role', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering = ['last_name', 'first_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations EEBC', {
            'fields': ('role', 'phone', 'photo', 'date_joined_church')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations EEBC', {
            'fields': ('role', 'phone', 'first_name', 'last_name', 'email')
        }),
    )

