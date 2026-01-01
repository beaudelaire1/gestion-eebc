"""Admin pour le module Worship."""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    WorshipService, ServiceRole, ServicePlanItem,
    ServiceTemplate, ServiceTemplateItem
)


class ServiceRoleInline(admin.TabularInline):
    """Inline pour les rôles d'un service."""
    model = ServiceRole
    extra = 1
    fields = ['role', 'member', 'user', 'status', 'notes']
    autocomplete_fields = ['member', 'user']


class ServicePlanItemInline(admin.TabularInline):
    """Inline pour le déroulement d'un service."""
    model = ServicePlanItem
    extra = 1
    fields = ['order', 'item_type', 'title', 'start_time', 'duration_minutes', 'responsible']
    autocomplete_fields = ['responsible']
    ordering = ['order']


@admin.register(WorshipService)
class WorshipServiceAdmin(admin.ModelAdmin):
    """Admin pour les services de culte."""
    
    list_display = [
        'event', 'service_type', 'theme', 'is_confirmed',
        'roles_status', 'actual_attendance'
    ]
    list_filter = ['service_type', 'is_confirmed', 'event__start_date']
    search_fields = ['theme', 'sermon_title', 'bible_text']
    date_hierarchy = 'event__start_date'
    autocomplete_fields = ['event']
    inlines = [ServiceRoleInline, ServicePlanItemInline]
    
    fieldsets = (
        ('Service', {
            'fields': ('event', 'service_type', 'is_confirmed')
        }),
        ('Contenu', {
            'fields': ('theme', 'bible_text', 'sermon_title', 'sermon_notes')
        }),
        ('Statistiques', {
            'fields': ('expected_attendance', 'actual_attendance', 'offering_total'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def roles_status(self, obj):
        """Affiche le statut des rôles assignés."""
        total = obj.roles.count()
        confirmed = obj.roles.filter(status='confirme').count()
        
        if total == 0:
            return format_html('<span class="badge bg-secondary">Aucun rôle</span>')
        
        if confirmed == total:
            color = 'success'
        elif confirmed > 0:
            color = 'warning'
        else:
            color = 'danger'
        
        return format_html(
            '<span class="badge bg-{}">{}/{} confirmés</span>',
            color, confirmed, total
        )
    roles_status.short_description = 'Rôles'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ServiceRole)
class ServiceRoleAdmin(admin.ModelAdmin):
    """Admin pour les rôles de service."""
    
    list_display = ['service', 'role', 'assignee_name', 'status_badge', 'notified_at']
    list_filter = ['role', 'status', 'service__event__start_date']
    search_fields = ['member__first_name', 'member__last_name', 'user__username']
    autocomplete_fields = ['service', 'member', 'user', 'replaced_by']
    
    def status_badge(self, obj):
        colors = {
            'en_attente': 'warning', 'confirme': 'success',
            'decline': 'danger', 'remplace': 'info'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'


@admin.register(ServicePlanItem)
class ServicePlanItemAdmin(admin.ModelAdmin):
    """Admin pour les éléments de programme."""
    
    list_display = ['service', 'order', 'item_type', 'title', 'start_time', 'duration_minutes']
    list_filter = ['item_type', 'service__event__start_date']
    search_fields = ['title', 'notes']
    ordering = ['service', 'order']


class ServiceTemplateItemInline(admin.TabularInline):
    """Inline pour les éléments de modèle."""
    model = ServiceTemplateItem
    extra = 1
    fields = ['order', 'item_type', 'title', 'duration_minutes']
    ordering = ['order']


@admin.register(ServiceTemplate)
class ServiceTemplateAdmin(admin.ModelAdmin):
    """Admin pour les modèles de service."""
    
    list_display = ['name', 'service_type', 'estimated_duration', 'is_active']
    list_filter = ['service_type', 'is_active']
    search_fields = ['name', 'description']
    inlines = [ServiceTemplateItemInline]
