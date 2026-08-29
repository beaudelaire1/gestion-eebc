from django.contrib import admin
from django.utils.html import format_html
from .models import YouthGroup, YoungMember, YouthEvent, YouthAttendance


@admin.register(YouthGroup)
class YouthGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'min_age', 'max_age', 'color_badge', 'members_count', 'is_active']
    list_filter = ['is_active']
    ordering = ['min_age']

    @admin.display(description='Couleur')
    def color_badge(self, obj):
        return format_html(
            '<span style="display:inline-block;width:60px;padding:4px 8px;background:{};color:white;'
            'border-radius:4px;text-align:center;font-size:11px;">{}</span>',
            obj.color, obj.color,
        )


class YouthAttendanceInline(admin.TabularInline):
    model = YouthAttendance
    extra = 0
    fields = ['young_member', 'status', 'transported', 'check_in_time']
    autocomplete_fields = ['young_member']


@admin.register(YoungMember)
class YoungMemberAdmin(admin.ModelAdmin):
    list_display = [
        'photo_thumbnail', 'last_name', 'first_name', 'age',
        'group', 'is_baptized', 'needs_transport', 'status',
    ]
    list_display_links = ['photo_thumbnail', 'last_name', 'first_name']
    list_filter = ['status', 'is_active', 'group', 'is_baptized', 'needs_transport', 'gender']
    search_fields = ['first_name', 'last_name', 'phone', 'email', 'parent_name']
    date_hierarchy = 'registration_date'
    list_per_page = 25

    fieldsets = (
        ('Identité', {
            'fields': (
                'first_name', 'last_name', 'date_of_birth', 'gender',
                'photo', 'site', 'group', 'linked_member',
            ),
        }),
        ('Coordonnées', {
            'fields': ('phone', 'email', 'address', 'city', 'postal_code'),
        }),
        ('Parent / Tuteur', {
            'fields': ('family', 'parent_name', 'parent_phone', 'parent_email'),
            'classes': ('collapse',),
        }),
        ('Contact d\'urgence', {
            'fields': ('emergency_contact', 'emergency_phone'),
            'classes': ('collapse',),
        }),
        ('Santé', {
            'fields': ('allergies', 'medical_notes'),
            'classes': ('collapse',),
        }),
        ('Vie spirituelle', {
            'fields': ('is_baptized', 'baptism_date', 'is_born_again', 'conversion_date'),
        }),
        ('Transport', {
            'fields': ('needs_transport', 'pickup_address', 'assigned_driver'),
            'classes': ('collapse',),
        }),
        ('Statut', {
            'fields': ('status', 'is_active', 'registration_date', 'notes'),
        }),
    )
    actions = ['print_registration_form']

    @admin.action(description="Imprimer la fiche d'inscription en PDF")
    def print_registration_form(self, request, queryset):
        from apps.core.pdf_service import PDFService
        
        if queryset.count() == 1:
            youth = queryset.first()
            context = {'youth': youth}
            filename = f"Fiche_Inscription_Jeune_{youth.id}.pdf"
            return PDFService.generate_pdf_download('young/pdf/registration_form.html', context, filename, request)
        else:
            self.message_user(request, "Veuillez sélectionner un seul jeune à la fois pour l'impression.", level='WARNING')
    @admin.display(description='Photo')
    def photo_thumbnail(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;'
                'border:2px solid #10b981;" />',
                obj.photo.url,
            )
        colors = ['#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#ef4444']
        color = colors[hash(obj.last_name) % len(colors)] if obj.last_name else '#6b7280'
        initials = (
            obj.first_name[0].upper() + obj.last_name[0].upper()
            if obj.first_name and obj.last_name else '?'
        )
        return format_html(
            '<div style="width:40px;height:40px;border-radius:50%;background:{};display:flex;'
            'align-items:center;justify-content:center;color:white;font-weight:bold;font-size:14px;">'
            '{}</div>',
            color, initials,
        )


@admin.register(YouthEvent)
class YouthEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'date', 'location', 'is_cancelled']
    list_filter = ['event_type', 'is_cancelled', 'date']
    search_fields = ['title', 'location', 'description']
    date_hierarchy = 'date'
    inlines = [YouthAttendanceInline]


@admin.register(YouthAttendance)
class YouthAttendanceAdmin(admin.ModelAdmin):
    list_display = ['young_member', 'event', 'status', 'transported', 'check_in_time']
    list_filter = ['status', 'transported']
    search_fields = ['young_member__first_name', 'young_member__last_name']
    autocomplete_fields = ['young_member', 'event']
