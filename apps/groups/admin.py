from django.contrib import admin
from .models import Group, GroupMeeting


class GroupMeetingInline(admin.TabularInline):
    model = GroupMeeting
    extra = 0
    fields = ['date', 'time', 'topic', 'attendees_count', 'is_cancelled']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'group_type', 'leader', 'member_count', 'meeting_day', 
                    'meeting_time', 'is_active']
    list_filter = ['group_type', 'is_active', 'meeting_day']
    search_fields = ['name', 'description']
    filter_horizontal = ['members']
    inlines = [GroupMeetingInline]
    
    fieldsets = (
        ('Informations', {
            'fields': ('name', 'description', 'group_type', 'leader', 'image', 'color')
        }),
        ('Membres', {
            'fields': ('members',)
        }),
        ('Horaires', {
            'fields': ('meeting_day', 'meeting_time', 'meeting_location', 'meeting_frequency')
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
    )


@admin.register(GroupMeeting)
class GroupMeetingAdmin(admin.ModelAdmin):
    list_display = ['group', 'date', 'time', 'topic', 'attendees_count', 'is_cancelled']
    list_filter = ['group', 'is_cancelled', 'date']
    search_fields = ['group__name', 'topic']
    date_hierarchy = 'date'

