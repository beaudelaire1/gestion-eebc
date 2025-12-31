from django.contrib import admin
from .models import EventCategory, Event, EventRegistration


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'icon']
    search_fields = ['name']


class EventRegistrationInline(admin.TabularInline):
    model = EventRegistration
    extra = 0
    readonly_fields = ['registered_at']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'start_date', 'start_time', 'location', 
                    'visibility', 'is_cancelled']
    list_filter = ['visibility', 'is_cancelled', 'category', 'recurrence']
    search_fields = ['title', 'description', 'location']
    date_hierarchy = 'start_date'
    inlines = [EventRegistrationInline]
    
    fieldsets = (
        ('Informations', {
            'fields': ('title', 'description', 'category', 'image')
        }),
        ('Date et Heure', {
            'fields': ('start_date', 'start_time', 'end_date', 'end_time', 'all_day')
        }),
        ('Lieu', {
            'fields': ('location', 'address')
        }),
        ('Récurrence', {
            'fields': ('recurrence', 'recurrence_end_date'),
            'classes': ('collapse',)
        }),
        ('Paramètres', {
            'fields': ('visibility', 'organizer', 'department', 'group', 'notify_before', 'is_cancelled')
        }),
    )


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ['event', 'user', 'registered_at']
    list_filter = ['event', 'registered_at']
    search_fields = ['user__first_name', 'user__last_name', 'event__title']

