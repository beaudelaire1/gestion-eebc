from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import (
    Site, City, Neighborhood, Family, FamilyRelationship, MissionCampaign,
    PageContent, NewsArticle, ContactMessage, VisitorRegistration,
    PublicEvent, Slider, SiteSettings
)
from .widgets import TinyMCEWidget


# =============================================================================
# FORMULAIRES AVEC TINYMCE
# =============================================================================

class PageContentAdminForm(forms.ModelForm):
    """Formulaire admin avec TinyMCE pour le contenu des pages."""
    class Meta:
        model = PageContent
        fields = '__all__'
        widgets = {
            'content': TinyMCEWidget(),
        }


class NewsArticleAdminForm(forms.ModelForm):
    """Formulaire admin avec TinyMCE pour les articles."""
    class Meta:
        model = NewsArticle
        fields = '__all__'
        widgets = {
            'content': TinyMCEWidget(),
        }


class AnnouncementAdminForm(forms.ModelForm):
    """Formulaire admin avec TinyMCE pour les annonces."""
    class Meta:
        fields = '__all__'
        widgets = {
            'content': TinyMCEWidget(config={'height': 300}),
        }


# =============================================================================
# INLINE POUR LES QUARTIERS
# =============================================================================

class NeighborhoodInline(admin.TabularInline):
    """Inline pour ajouter des quartiers directement depuis une ville."""
    model = Neighborhood
    extra = 3  # 3 lignes vides pour ajouter rapidement
    fields = ['name', 'zone_leader', 'is_active']
    autocomplete_fields = ['zone_leader']


# =============================================================================
# ADMIN SITE
# =============================================================================

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'city', 'pastor', 'member_count', 'is_main_site', 'is_active']
    list_filter = ['is_active', 'is_main_site']
    search_fields = ['name', 'code', 'city']
    filter_horizontal = ['administrators']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('code', 'name', 'is_main_site', 'is_active'),
            'description': 'Le code est utilisé pour générer les IDs membres (ex: EEBC-CAB-XXXX)'
        }),
        ('Adresse', {
            'fields': ('address', 'city', 'postal_code')
        }),
        ('Contact', {
            'fields': ('phone', 'email')
        }),
        ('Coordonnées GPS', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',),
            'description': 'Pour affichage sur carte'
        }),
        ('Horaires des cultes', {
            'fields': ('worship_schedule',)
        }),
        ('Responsables', {
            'fields': ('pastor', 'administrators')
        }),
    )
    
    def member_count(self, obj):
        count = obj.members.count()
        return format_html('<span class="badge bg-primary">{}</span>', count)
    member_count.short_description = 'Membres'
    
    def save_model(self, request, obj, form, change):
        # Convertir le code en majuscules
        obj.code = obj.code.upper()
        super().save_model(request, obj, form, change)


# =============================================================================
# ADMIN VILLE
# =============================================================================

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'postal_code', 'neighborhood_count_display', 'family_count_display', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'postal_code']
    inlines = [NeighborhoodInline]  # Permet d'ajouter des quartiers directement
    
    fieldsets = (
        ('Informations', {
            'fields': ('name', 'postal_code', 'is_active')
        }),
        ('Coordonnées GPS', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
    )
    
    def neighborhood_count_display(self, obj):
        count = obj.neighborhood_count
        return format_html('<span class="badge bg-info">{}</span>', count)
    neighborhood_count_display.short_description = 'Quartiers'
    
    def family_count_display(self, obj):
        count = obj.family_count
        return format_html('<span class="badge bg-success">{}</span>', count)
    family_count_display.short_description = 'Familles'


# =============================================================================
# ADMIN QUARTIER
# =============================================================================

@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'zone_leader', 'family_count_display', 'is_active']
    list_filter = ['city', 'is_active']
    search_fields = ['name', 'city__name']
    autocomplete_fields = ['city', 'zone_leader']
    list_editable = ['is_active']  # Permet d'activer/désactiver rapidement
    
    fieldsets = (
        ('Informations', {
            'fields': ('name', 'city', 'description', 'is_active')
        }),
        ('Coordonnées GPS', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Recensement', {
            'fields': ('estimated_population', 'last_census_date'),
            'classes': ('collapse',)
        }),
        ('Responsable', {
            'fields': ('zone_leader',)
        }),
    )
    
    def family_count_display(self, obj):
        count = obj.family_count
        return format_html('<span class="badge bg-success">{}</span>', count)
    family_count_display.short_description = 'Familles'


# =============================================================================
# ADMIN FAMILLE
# =============================================================================

@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ['name', 'site', 'neighborhood', 'city', 'member_count_display', 'phone', 'is_active']
    list_filter = ['site', 'neighborhood__city', 'is_active']
    search_fields = ['name', 'address', 'phone', 'email']
    autocomplete_fields = ['site', 'neighborhood']
    
    fieldsets = (
        ('Informations', {
            'fields': ('name', 'site', 'is_active')
        }),
        ('Localisation', {
            'fields': ('neighborhood', 'address', 'city', 'postal_code')
        }),
        ('Coordonnées GPS', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Contact', {
            'fields': ('phone', 'email')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def member_count_display(self, obj):
        count = obj.member_count
        return format_html('<span class="badge bg-primary">{}</span>', count)
    member_count_display.short_description = 'Membres'


# =============================================================================
# ADMIN RELATIONS FAMILIALES
# =============================================================================

@admin.register(FamilyRelationship)
class FamilyRelationshipAdmin(admin.ModelAdmin):
    list_display = ['from_member', 'relationship_type', 'to_member']
    list_filter = ['relationship_type']
    search_fields = ['from_member__first_name', 'from_member__last_name', 
                     'to_member__first_name', 'to_member__last_name']
    autocomplete_fields = ['from_member', 'to_member']


# =============================================================================
# ADMIN CAMPAGNES DE MISSION
# =============================================================================

@admin.register(MissionCampaign)
class MissionCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'site', 'start_date', 'end_date', 'status_badge', 'leader', 'homes_visited', 'contacts_made']
    list_filter = ['site', 'status', 'start_date']
    search_fields = ['name', 'description']
    filter_horizontal = ['neighborhoods', 'team_members']
    autocomplete_fields = ['site', 'leader']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Informations', {
            'fields': ('name', 'description', 'site', 'status')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Zones ciblées', {
            'fields': ('neighborhoods',)
        }),
        ('Équipe', {
            'fields': ('leader', 'team_members')
        }),
        ('Résultats', {
            'fields': ('homes_visited', 'contacts_made', 'decisions_made'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'planned': 'info',
            'in_progress': 'warning',
            'completed': 'success',
            'cancelled': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'



# =============================================================================
# SITE VITRINE - ADMIN
# =============================================================================

@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    form = PageContentAdminForm
    list_display = ['title', 'page_type', 'is_published', 'show_in_menu', 'menu_order', 'updated_at']
    list_filter = ['page_type', 'is_published', 'show_in_menu']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['is_published', 'show_in_menu', 'menu_order']
    
    fieldsets = (
        ('Informations', {
            'fields': ('page_type', 'title', 'slug', 'subtitle')
        }),
        ('Contenu', {
            'fields': ('content', 'header_image')
        }),
        ('SEO', {
            'fields': ('meta_description',),
            'classes': ('collapse',)
        }),
        ('Paramètres', {
            'fields': ('is_published', 'show_in_menu', 'menu_order')
        }),
    )
    
    class Media:
        js = ('https://cdn.tiny.cloud/1/6qr0im1d33wizm1ytimh1kpwbugqeb8r4fq1gebb03rme6hv/tinymce/6/tinymce.min.js',)
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    form = NewsArticleAdminForm
    list_display = ['title', 'category', 'display_author', 'site', 'is_published', 'is_featured', 'publish_date', 'visibility_status', 'views_count']
    list_filter = ['category', 'site', 'is_published', 'is_featured']
    search_fields = ['title', 'excerpt', 'content', 'author_name']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['is_published', 'is_featured']
    date_hierarchy = 'publish_date'
    
    fieldsets = (
        ('Informations', {
            'fields': ('title', 'slug', 'category', 'site')
        }),
        ('Auteur', {
            'fields': ('author_name', 'author'),
            'description': 'Le nom de l\'auteur est requis pour les méditations. Pour les actualités, il est optionnel.'
        }),
        ('Contenu', {
            'fields': ('excerpt', 'content', 'featured_image')
        }),
        ('Publication', {
            'fields': ('is_published', 'is_featured', 'publish_date')
        }),
        ('Période d\'affichage', {
            'fields': ('display_start_date', 'display_end_date'),
            'description': 'Optionnel : définir une période pendant laquelle l\'article est visible.',
            'classes': ('collapse',)
        }),
    )
    
    def display_author(self, obj):
        author = obj.display_author
        if author:
            return author
        if obj.category == 'devotional':
            return format_html('<span style="color: red;">⚠ Requis</span>')
        return '-'
    display_author.short_description = 'Auteur'
    
    def visibility_status(self, obj):
        if obj.is_visible:
            return format_html('<span class="badge bg-success">Visible</span>')
        elif not obj.is_published:
            return format_html('<span class="badge bg-secondary">Non publié</span>')
        else:
            return format_html('<span class="badge bg-warning">Hors période</span>')
    visibility_status.short_description = 'Visibilité'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'site', 'status_badge', 'assigned_to', 'created_at']
    list_filter = ['status', 'subject', 'site']
    search_fields = ['name', 'email', 'message']
    readonly_fields = ['name', 'email', 'phone', 'subject', 'message', 'site', 'ip_address', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Message', {
            'fields': ('name', 'email', 'phone', 'subject', 'message', 'site')
        }),
        ('Suivi', {
            'fields': ('status', 'assigned_to', 'notes')
        }),
        ('Métadonnées', {
            'fields': ('ip_address', 'created_at', 'read_at', 'replied_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'new': 'danger',
            'read': 'warning',
            'replied': 'success',
            'archived': 'secondary',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        # Marquer comme lu automatiquement
        obj = self.get_object(request, object_id)
        if obj and obj.status == 'new':
            obj.mark_as_read()
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(VisitorRegistration)
class VisitorRegistrationAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'interest', 'preferred_site', 'is_contacted', 'created_at']
    list_filter = ['interest', 'preferred_site', 'is_contacted', 'neighborhood__city']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    date_hierarchy = 'created_at'
    autocomplete_fields = ['neighborhood', 'preferred_site', 'contacted_by', 'converted_to_member']
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Adresse', {
            'fields': ('address', 'city', 'neighborhood'),
            'classes': ('collapse',)
        }),
        ('Intérêt', {
            'fields': ('interest', 'preferred_site', 'message')
        }),
        ('Suivi', {
            'fields': ('is_contacted', 'contacted_by', 'contacted_at', 'converted_to_member', 'notes')
        }),
    )
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Nom'


@admin.register(PublicEvent)
class PublicEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'site', 'start_date', 'start_time', 'is_published', 'is_featured', 'allow_registration']
    list_filter = ['site', 'is_published', 'is_featured', 'allow_registration']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['is_published', 'is_featured']
    date_hierarchy = 'start_date'
    autocomplete_fields = ['site', 'internal_event']
    
    fieldsets = (
        ('Informations', {
            'fields': ('title', 'slug', 'description', 'internal_event')
        }),
        ('Date et lieu', {
            'fields': ('start_date', 'start_time', 'end_date', 'end_time', 'location', 'address', 'site')
        }),
        ('Image', {
            'fields': ('image',)
        }),
        ('Paramètres', {
            'fields': ('is_published', 'is_featured', 'allow_registration')
        }),
    )


@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    list_display = ['title', 'image_preview', 'is_active', 'order']
    list_filter = ['is_active']
    list_editable = ['is_active', 'order']
    
    fieldsets = (
        ('Contenu', {
            'fields': ('title', 'subtitle', 'image')
        }),
        ('Bouton', {
            'fields': ('button_text', 'button_url'),
            'classes': ('collapse',)
        }),
        ('Paramètres', {
            'fields': ('is_active', 'order')
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 50px;" />',
                obj.image.url
            )
        return "-"
    image_preview.short_description = 'Aperçu'


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin pour les paramètres du site (singleton)."""
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('site_name', 'tagline', 'logo', 'favicon')
        }),
        ('Contact', {
            'fields': ('email', 'phone')
        }),
        ('Réseaux sociaux', {
            'fields': ('facebook_url', 'youtube_url', 'instagram_url'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_description',),
            'classes': ('collapse',)
        }),
        ('Pied de page', {
            'fields': ('footer_text',),
            'classes': ('collapse',)
        }),
        ('Maintenance', {
            'fields': ('maintenance_mode', 'maintenance_message'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Empêcher la création de plusieurs instances
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
