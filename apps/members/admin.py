from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import Member, LifeEvent, VisitationLog


class MemberAdminForm(forms.ModelForm):
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
        model = Member
        fields = '__all__'


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    form = MemberAdminForm  # Utiliser le formulaire personnalisé
    list_display = ['photo_thumbnail', 'last_name', 'first_name', 'phone', 'email', 'status', 'is_baptized', 'date_joined']
    list_display_links = ['photo_thumbnail', 'last_name', 'first_name']
    list_filter = ['status', 'is_baptized', 'gender', 'marital_status', 'city']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'address']
    ordering = ['last_name', 'first_name']
    date_hierarchy = 'date_joined'
    list_per_page = 25
    
    fieldsets = (
        ('Identité', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'gender', 'photo', 'photo_preview')
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'address', 'city', 'postal_code')
        }),
        ('Situation', {
            'fields': ('marital_status', 'profession')
        }),
        ('Église', {
            'fields': ('user', 'status', 'date_joined', 'is_baptized', 'baptism_date')
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
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 2px solid #0A36FF;" />',
                obj.photo.url
            )
        return format_html(
            '<div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #0A36FF 0%, #3b82f6 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px;">{}</div>',
            obj.first_name[0].upper() + obj.last_name[0].upper() if obj.first_name and obj.last_name else '?'
        )
    
    @admin.display(description='Aperçu photo')
    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" />',
                obj.photo.url
            )
        return format_html(
            '<div style="width: 150px; height: 150px; border-radius: 10px; background: linear-gradient(135deg, #0A36FF 0%, #3b82f6 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 48px;">{}</div>',
            obj.first_name[0].upper() + obj.last_name[0].upper() if obj.first_name and obj.last_name else '?'
        )


# =============================================================================
# PASTORAL CRM - Admin pour LifeEvent et VisitationLog
# =============================================================================

class VisitationLogInline(admin.TabularInline):
    """Inline pour les visites d'un membre."""
    model = VisitationLog
    extra = 0
    fields = ['visit_date', 'visit_type', 'status', 'visitor', 'summary']
    readonly_fields = ['visit_date']
    ordering = ['-visit_date']
    max_num = 5


class LifeEventInline(admin.TabularInline):
    """Inline pour les événements de vie d'un membre."""
    model = LifeEvent
    fk_name = 'primary_member'
    extra = 0
    fields = ['event_type', 'event_date', 'title', 'requires_visit', 'visit_completed']
    ordering = ['-event_date']
    max_num = 5


# Ajouter les inlines au MemberAdmin existant
MemberAdmin.inlines = [LifeEventInline, VisitationLogInline]


@admin.register(LifeEvent)
class LifeEventAdmin(admin.ModelAdmin):
    """Admin pour les événements de vie."""
    
    list_display = [
        'title', 'event_type_badge', 'primary_member', 'event_date',
        'priority_badge', 'requires_visit', 'visit_completed', 'announce_sunday'
    ]
    list_filter = ['event_type', 'priority', 'requires_visit', 'visit_completed', 
                   'announce_sunday', 'event_date']
    search_fields = ['title', 'description', 'primary_member__first_name', 
                     'primary_member__last_name']
    date_hierarchy = 'event_date'
    autocomplete_fields = ['primary_member', 'related_members']
    
    fieldsets = (
        ('Événement', {
            'fields': ('event_type', 'title', 'event_date', 'priority')
        }),
        ('Personnes concernées', {
            'fields': ('primary_member', 'related_members')
        }),
        ('Détails', {
            'fields': ('description',)
        }),
        ('Suivi pastoral', {
            'fields': ('requires_visit', 'visit_completed', 'announce_sunday', 'announced')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def event_type_badge(self, obj):
        colors = {
            'naissance': 'success', 'mariage': 'primary', 'bapteme': 'info',
            'deces': 'dark', 'deuil': 'secondary', 'hospitalisation': 'warning',
            'conversion': 'success', 'autre': 'light'
        }
        color = colors.get(obj.event_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_event_type_display()
        )
    event_type_badge.short_description = 'Type'
    
    def priority_badge(self, obj):
        colors = {'haute': 'danger', 'normale': 'warning', 'basse': 'secondary'}
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.priority, 'secondary'),
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priorité'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(VisitationLog)
class VisitationLogAdmin(admin.ModelAdmin):
    """Admin pour le journal des visites."""
    
    list_display = [
        'member', 'visit_type', 'status_badge', 'visit_date', 
        'visitor', 'follow_up_needed', 'is_confidential'
    ]
    list_filter = ['status', 'visit_type', 'follow_up_needed', 'is_confidential', 'visit_date']
    search_fields = ['member__first_name', 'member__last_name', 'summary', 'prayer_requests']
    date_hierarchy = 'visit_date'
    autocomplete_fields = ['member', 'visitor', 'life_event']
    
    fieldsets = (
        ('Visite', {
            'fields': ('member', 'visitor', 'visit_type', 'status')
        }),
        ('Dates', {
            'fields': ('scheduled_date', 'visit_date', 'duration_minutes')
        }),
        ('Lien événement', {
            'fields': ('life_event',),
            'classes': ('collapse',)
        }),
        ('Compte-rendu', {
            'fields': ('summary', 'prayer_requests')
        }),
        ('Suivi', {
            'fields': ('follow_up_needed', 'follow_up_notes', 'is_confidential')
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'planifie': 'info', 'a_faire': 'warning', 'effectue': 'success',
            'annule': 'danger', 'reporte': 'secondary'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def get_queryset(self, request):
        """Filtre les visites confidentielles pour les non-superusers."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Les non-superusers ne voient pas les visites confidentielles des autres
            qs = qs.filter(
                models.Q(is_confidential=False) | 
                models.Q(visitor=request.user)
            )
        return qs
