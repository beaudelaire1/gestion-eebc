from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import AgeGroup, BibleClass, Monitor, Child, Session, Attendance, DriverCheckIn


class ChildAdminForm(forms.ModelForm):
    """Formulaire personnalisé pour forcer le widget file standard."""
    photo = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'accept': 'image/*',
            'class': 'form-control',
            'style': 'display: block !important; opacity: 1 !important; position: relative !important;'
        }),
        label="Photo"
    )
    
    class Meta:
        model = Child
        fields = '__all__'


@admin.register(AgeGroup)
class AgeGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'min_age', 'max_age', 'color_badge']
    ordering = ['min_age']
    
    @admin.display(description='Couleur')
    def color_badge(self, obj):
        return format_html(
            '<span style="display: inline-block; width: 60px; padding: 4px 8px; background: {}; color: white; border-radius: 4px; text-align: center; font-size: 11px;">{}</span>',
            obj.color, obj.color
        )


class MonitorInline(admin.TabularInline):
    model = Monitor
    extra = 0
    readonly_fields = ['user']


class ChildInline(admin.TabularInline):
    model = Child
    extra = 0
    fields = ['first_name', 'last_name', 'date_of_birth', 'is_active']
    readonly_fields = ['first_name', 'last_name', 'date_of_birth']
    can_delete = False
    show_change_link = True


@admin.register(BibleClass)
class BibleClassAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'age_group', 'room', 'children_count', 'monitors_count', 'is_active']
    list_filter = ['is_active', 'age_group']
    search_fields = ['room', 'age_group__name']
    inlines = [MonitorInline]
    
    def children_count(self, obj):
        return obj.children_count
    children_count.short_description = "Enfants"
    
    def monitors_count(self, obj):
        return obj.monitors.filter(is_active=True).count()
    monitors_count.short_description = "Moniteurs"


@admin.register(Monitor)
class MonitorAdmin(admin.ModelAdmin):
    list_display = ['user', 'bible_class', 'is_lead', 'phone', 'is_active']
    list_filter = ['is_active', 'is_lead', 'bible_class']
    search_fields = ['user__first_name', 'user__last_name', 'phone']
    autocomplete_fields = ['user', 'bible_class']


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    form = ChildAdminForm  # Utiliser le formulaire personnalisé
    list_display = ['photo_thumbnail', 'last_name', 'first_name', 'age', 'bible_class', 'father_name',
                    'needs_transport', 'is_active']
    list_display_links = ['photo_thumbnail', 'last_name', 'first_name']
    list_filter = ['is_active', 'bible_class', 'needs_transport', 'gender']
    search_fields = ['first_name', 'last_name', 'father_name', 'father_phone',
                     'mother_name', 'mother_phone']
    date_hierarchy = 'registration_date'
    list_per_page = 25
    
    fieldsets = (
        ('Identité', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'gender', 'photo', 'photo_preview')
        }),
        ('Classe', {
            'fields': ('bible_class', 'is_active')
        }),
        ('Pere', {
            'fields': ('father_name', 'father_phone', 'father_email')
        }),
        ('Mere', {
            'fields': ('mother_name', 'mother_phone', 'mother_email'),
            'classes': ('collapse',)
        }),
        ('Contact d\'urgence', {
            'fields': ('emergency_contact', 'emergency_phone'),
            'classes': ('collapse',)
        }),
        ('Santé', {
            'fields': ('allergies', 'medical_notes'),
            'classes': ('collapse',)
        }),
        ('Transport', {
            'fields': ('needs_transport', 'pickup_address', 'assigned_driver'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['photo_preview']
    
    @admin.display(description='Photo')
    def photo_thumbnail(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 2px solid #10b981;" />',
                obj.photo.url
            )
        # Avatar avec initiales
        colors = ['#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#ef4444']
        color = colors[hash(obj.last_name) % len(colors)] if obj.last_name else '#6b7280'
        return format_html(
            '<div style="width: 40px; height: 40px; border-radius: 50%; background: {}; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px;">{}</div>',
            color,
            obj.first_name[0].upper() + obj.last_name[0].upper() if obj.first_name and obj.last_name else '?'
        )
    
    @admin.display(description='Aperçu photo')
    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" />',
                obj.photo.url
            )
        colors = ['#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#ef4444']
        color = colors[hash(obj.last_name) % len(colors)] if obj.last_name else '#6b7280'
        return format_html(
            '<div style="width: 150px; height: 150px; border-radius: 10px; background: {}; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 48px;">{}</div>',
            color,
            obj.first_name[0].upper() + obj.last_name[0].upper() if obj.first_name and obj.last_name else '?'
        )


class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    fields = ['child', 'bible_class', 'status', 'check_in_time', 'check_out_time']
    autocomplete_fields = ['child']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['date', 'theme', 'attendance_count', 'is_cancelled']
    list_filter = ['is_cancelled']
    search_fields = ['theme', 'notes']
    date_hierarchy = 'date'
    inlines = [AttendanceInline]
    
    def attendance_count(self, obj):
        present = obj.attendances.filter(status__in=['present', 'late']).count()
        total = obj.attendances.count()
        return f"{present}/{total}"
    attendance_count.short_description = "Présences"


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['child', 'session', 'bible_class', 'status', 'check_in_time']
    list_filter = ['status', 'session__date', 'bible_class']
    search_fields = ['child__first_name', 'child__last_name']
    date_hierarchy = 'session__date'
    autocomplete_fields = ['child', 'session', 'bible_class']


@admin.register(DriverCheckIn)
class DriverCheckInAdmin(admin.ModelAdmin):
    list_display = ['driver', 'session', 'departure_time', 'arrival_time', 'children_count']
    list_filter = ['session__date']
    search_fields = ['driver__user__first_name', 'driver__user__last_name']
    filter_horizontal = ['children_picked_up']
    
    def children_count(self, obj):
        return obj.children_picked_up.count()
    children_count.short_description = "Enfants transportés"
