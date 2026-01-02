"""Admin pour le module Worship."""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseRedirect
from .models import (
    WorshipService, ServiceRole, ServicePlanItem,
    ServiceTemplate, ServiceTemplateItem,
    MonthlySchedule, ScheduledService, ServiceNotification
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


# =============================================================================
# PLANIFICATION MENSUELLE
# =============================================================================

class ScheduledServiceInline(admin.TabularInline):
    """Inline pour les cultes d'un planning mensuel."""
    model = ScheduledService
    extra = 0
    fields = ['date', 'start_time', 'preacher', 'worship_leader', 'choir_leader', 'theme', 'notifications_sent']
    readonly_fields = ['notifications_sent']
    autocomplete_fields = ['preacher', 'worship_leader', 'choir_leader']
    ordering = ['date']
    
    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return 0
        return 5  # 5 dimanches par défaut pour un nouveau planning


@admin.register(MonthlySchedule)
class MonthlyScheduleAdmin(admin.ModelAdmin):
    """Admin pour les plannings mensuels."""
    
    list_display = [
        'month_year', 'site', 'status_badge', 'services_count',
        'notification_config', 'created_by', 'actions_buttons'
    ]
    list_filter = ['status', 'site', 'year']
    search_fields = ['site__name', 'notes']
    autocomplete_fields = ['site']
    inlines = [ScheduledServiceInline]
    
    fieldsets = (
        ('Période', {
            'fields': ('year', 'month', 'site')
        }),
        ('Statut', {
            'fields': ('status',)
        }),
        ('Configuration des notifications', {
            'fields': (
                'notification_day', 'days_before_service',
                'notify_by_email', 'notify_by_sms', 'notify_by_whatsapp'
            ),
            'description': 'Configurez quand et comment les participants seront notifiés.'
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def month_year(self, obj):
        return f"{obj.month_name} {obj.year}"
    month_year.short_description = 'Mois'
    month_year.admin_order_field = 'year'
    
    def status_badge(self, obj):
        colors = {
            'brouillon': 'secondary',
            'en_cours': 'warning',
            'valide': 'info',
            'publie': 'success'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def services_count(self, obj):
        count = obj.services.count()
        return format_html('<span class="badge bg-primary">{} cultes</span>', count)
    services_count.short_description = 'Cultes'
    
    def notification_config(self, obj):
        days = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
        channels = []
        if obj.notify_by_email:
            channels.append('📧')
        if obj.notify_by_sms:
            channels.append('📱')
        if obj.notify_by_whatsapp:
            channels.append('💬')
        
        return format_html(
            '{} (J-{}) {}',
            days[obj.notification_day],
            obj.days_before_service,
            ' '.join(channels)
        )
    notification_config.short_description = 'Notifications'
    
    def actions_buttons(self, obj):
        buttons = []
        
        if obj.status == 'brouillon':
            buttons.append(
                f'<a class="button" href="{obj.id}/generate-sundays/" '
                f'style="background:#17a2b8;color:white;padding:3px 8px;border-radius:3px;margin-right:5px;">'
                f'Générer dimanches</a>'
            )
        
        if obj.status in ['brouillon', 'en_cours', 'valide']:
            buttons.append(
                f'<a class="button" href="{obj.id}/publish/" '
                f'style="background:#28a745;color:white;padding:3px 8px;border-radius:3px;margin-right:5px;">'
                f'Publier</a>'
            )
        
        if obj.status == 'publie':
            buttons.append(
                f'<a class="button" href="{obj.id}/send-notifications/" '
                f'style="background:#ffc107;color:#333;padding:3px 8px;border-radius:3px;">'
                f'Envoyer notifs</a>'
            )
        
        return format_html(''.join(buttons)) if buttons else '-'
    actions_buttons.short_description = 'Actions'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/generate-sundays/',
                 self.admin_site.admin_view(self.generate_sundays_view),
                 name='worship_monthlyschedule_generate'),
            path('<int:pk>/publish/',
                 self.admin_site.admin_view(self.publish_view),
                 name='worship_monthlyschedule_publish'),
            path('<int:pk>/send-notifications/',
                 self.admin_site.admin_view(self.send_notifications_view),
                 name='worship_monthlyschedule_send_notifs'),
        ]
        return custom_urls + urls
    
    def generate_sundays_view(self, request, pk):
        """Génère automatiquement les cultes pour tous les dimanches du mois."""
        schedule = get_object_or_404(MonthlySchedule, pk=pk)
        sundays = schedule.get_sundays()
        
        created = 0
        for sunday in sundays:
            _, was_created = ScheduledService.objects.get_or_create(
                schedule=schedule,
                date=sunday,
                defaults={'start_time': '09:30'}
            )
            if was_created:
                created += 1
        
        messages.success(request, f'{created} culte(s) créé(s) pour {schedule}')
        return HttpResponseRedirect(reverse('admin:worship_monthlyschedule_change', args=[pk]))
    
    def publish_view(self, request, pk):
        """Publie le planning et programme les notifications."""
        schedule = get_object_or_404(MonthlySchedule, pk=pk)
        schedule.publish()
        messages.success(request, f'Planning {schedule} publié avec succès !')
        return HttpResponseRedirect(reverse('admin:worship_monthlyschedule_change', args=[pk]))
    
    def send_notifications_view(self, request, pk):
        """Envoie les notifications pour tous les cultes non notifiés."""
        schedule = get_object_or_404(MonthlySchedule, pk=pk)
        
        sent = 0
        for service in schedule.services.filter(notifications_sent=False):
            try:
                service.send_notifications()
                sent += 1
            except Exception as e:
                messages.error(request, f'Erreur pour {service}: {e}')
        
        if sent:
            messages.success(request, f'Notifications envoyées pour {sent} culte(s)')
        else:
            messages.info(request, 'Aucune notification à envoyer')
        
        return HttpResponseRedirect(reverse('admin:worship_monthlyschedule_change', args=[pk]))
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ScheduledService)
class ScheduledServiceAdmin(admin.ModelAdmin):
    """Admin pour les cultes programmés."""
    
    list_display = [
        'date', 'schedule', 'preacher', 'worship_leader',
        'singers_count', 'musicians_count', 'notifications_badge'
    ]
    list_filter = ['schedule__site', 'schedule__year', 'schedule__month', 'notifications_sent']
    search_fields = ['theme', 'preacher__first_name', 'preacher__last_name']
    date_hierarchy = 'date'
    autocomplete_fields = [
        'schedule', 'preacher', 'worship_leader', 'choir_leader',
        'sound_tech', 'projection', 'singers', 'musicians'
    ]
    filter_horizontal = ['singers', 'musicians']
    
    fieldsets = (
        ('Planning', {
            'fields': ('schedule', 'date', 'start_time')
        }),
        ('Contenu', {
            'fields': ('theme', 'bible_text')
        }),
        ('Équipe principale', {
            'fields': ('preacher', 'worship_leader', 'choir_leader')
        }),
        ('Choristes et musiciens', {
            'fields': ('singers', 'musicians'),
            'classes': ('collapse',)
        }),
        ('Technique', {
            'fields': ('sound_tech', 'projection'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def singers_count(self, obj):
        count = obj.singers.count()
        return format_html('<span class="badge bg-info">{}</span>', count)
    singers_count.short_description = 'Choristes'
    
    def musicians_count(self, obj):
        count = obj.musicians.count()
        return format_html('<span class="badge bg-info">{}</span>', count)
    musicians_count.short_description = 'Musiciens'
    
    def notifications_badge(self, obj):
        if obj.notifications_sent:
            return format_html(
                '<span class="badge bg-success">✓ Envoyé</span>'
            )
        return format_html('<span class="badge bg-secondary">En attente</span>')
    notifications_badge.short_description = 'Notifs'


@admin.register(ServiceNotification)
class ServiceNotificationAdmin(admin.ModelAdmin):
    """Admin pour les notifications de culte."""
    
    list_display = [
        'scheduled_service', 'scheduled_date', 'status_badge',
        'channels', 'sent_at'
    ]
    list_filter = ['status', 'scheduled_date']
    readonly_fields = ['sent_at', 'error_message']
    
    actions = ['send_selected_notifications']
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'sent': 'success',
            'failed': 'danger',
            'cancelled': 'secondary'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def channels(self, obj):
        icons = []
        if obj.notify_email:
            icons.append('📧')
        if obj.notify_sms:
            icons.append('📱')
        if obj.notify_whatsapp:
            icons.append('💬')
        return ' '.join(icons) or '-'
    channels.short_description = 'Canaux'
    
    @admin.action(description='Envoyer les notifications sélectionnées')
    def send_selected_notifications(self, request, queryset):
        sent = 0
        for notif in queryset.filter(status='pending'):
            notif.send()
            if notif.status == 'sent':
                sent += 1
        
        messages.success(request, f'{sent} notification(s) envoyée(s)')
