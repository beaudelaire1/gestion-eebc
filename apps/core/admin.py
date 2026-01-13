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
        js = ('https://cdn.jsdelivr.net/npm/tinymce@6/tinymce.min.js',)
    
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


# =============================================================================
# AUDIT LOG ADMIN
# =============================================================================

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Administration du journal d'audit.
    
    Permet de consulter les logs d'audit avec filtrage et recherche.
    Les entrées sont en lecture seule pour préserver l'intégrité des logs.
    
    Requirements: 8.5
    """
    
    list_display = [
        'timestamp', 'user_display', 'action_badge', 'model_name', 
        'object_repr_short', 'ip_address'
    ]
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'model_name', 'object_repr', 'ip_address', 'path'
    ]
    readonly_fields = [
        'user', 'action', 'model_name', 'object_id', 'object_repr',
        'changes', 'ip_address', 'user_agent', 'timestamp', 'path', 'extra_data'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    list_per_page = 50
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('user', 'action', 'timestamp')
        }),
        ('Objet concerné', {
            'fields': ('model_name', 'object_id', 'object_repr')
        }),
        ('Détails des changements', {
            'fields': ('changes',),
            'classes': ('collapse',)
        }),
        ('Contexte de la requête', {
            'fields': ('ip_address', 'user_agent', 'path'),
            'classes': ('collapse',)
        }),
        ('Données supplémentaires', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Empêcher la création manuelle d'entrées d'audit."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Empêcher la modification des entrées d'audit."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Empêcher la suppression des entrées d'audit (sauf superuser)."""
        return request.user.is_superuser
    
    def user_display(self, obj):
        """Affiche le nom de l'utilisateur ou 'Anonyme'."""
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return format_html('<span style="color: #999;">Anonyme</span>')
    user_display.short_description = 'Utilisateur'
    user_display.admin_order_field = 'user__username'
    
    def action_badge(self, obj):
        """Affiche l'action avec un badge coloré."""
        colors = {
            'login': 'success',
            'logout': 'info',
            'login_failed': 'danger',
            'create': 'primary',
            'update': 'warning',
            'delete': 'danger',
            'export': 'info',
            'access_denied': 'danger',
            'view': 'secondary',
        }
        color = colors.get(obj.action, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_action_display()
        )
    action_badge.short_description = 'Action'
    action_badge.admin_order_field = 'action'
    
    def object_repr_short(self, obj):
        """Affiche une version tronquée de la représentation de l'objet."""
        if obj.object_repr:
            if len(obj.object_repr) > 50:
                return obj.object_repr[:50] + '...'
            return obj.object_repr
        return '-'
    object_repr_short.short_description = 'Objet'


# =============================================================================
# DATABASE BACKUP ADMIN
# =============================================================================

from .models import DatabaseBackup
from django.http import HttpResponse, Http404
from django.urls import path
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.utils.html import format_html
from pathlib import Path


@admin.register(DatabaseBackup)
class DatabaseBackupAdmin(admin.ModelAdmin):
    """
    Administration des sauvegardes de base de données.
    
    Permet de:
    - Lister les sauvegardes disponibles
    - Télécharger les sauvegardes
    - Déclencher une sauvegarde manuelle
    - Voir le statut des sauvegardes
    
    Requirements: 18.3
    """
    
    list_display = [
        'filename', 'status_badge', 'backup_type', 'file_size_display',
        'database_engine', 'created_by', 'created_at', 'download_link'
    ]
    list_filter = ['status', 'backup_type', 'database_engine', 'created_at']
    search_fields = ['filename', 'created_by__username']
    readonly_fields = [
        'filename', 'file_path', 'file_size', 'status', 'database_engine',
        'backup_type', 'created_by', 'celery_task_id', 'error_message',
        'created_at', 'completed_at', 'file_exists_display'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 25
    
    fieldsets = (
        ('Informations de la sauvegarde', {
            'fields': ('filename', 'file_path', 'file_size', 'file_exists_display')
        }),
        ('Statut', {
            'fields': ('status', 'error_message')
        }),
        ('Métadonnées', {
            'fields': ('backup_type', 'database_engine', 'created_by', 'celery_task_id')
        }),
        ('Dates', {
            'fields': ('created_at', 'completed_at')
        }),
    )
    
    def has_add_permission(self, request):
        """Empêcher la création manuelle - utiliser le bouton de sauvegarde."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Empêcher la modification des sauvegardes."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Permettre la suppression seulement aux admins."""
        return request.user.is_superuser
    
    def status_badge(self, obj):
        """Affiche le statut avec un badge coloré."""
        colors = {
            'pending': 'warning',
            'success': 'success',
            'failed': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    status_badge.admin_order_field = 'status'
    
    def file_size_display(self, obj):
        """Affiche la taille du fichier en format lisible."""
        if obj.file_size_mb:
            return f"{obj.file_size_mb} MB"
        return '-'
    file_size_display.short_description = 'Taille'
    file_size_display.admin_order_field = 'file_size'
    
    def file_exists_display(self, obj):
        """Indique si le fichier existe sur le disque."""
        if obj.file_exists:
            return format_html('<span style="color: green;">✓ Existe</span>')
        else:
            return format_html('<span style="color: red;">✗ Manquant</span>')
    file_exists_display.short_description = 'Fichier sur disque'
    
    def download_link(self, obj):
        """Lien de téléchargement si le fichier existe et la sauvegarde est réussie."""
        if obj.status == 'success' and obj.file_exists:
            return format_html(
                '<a href="{}" class="btn btn-sm btn-primary">Télécharger</a>',
                f'/admin/core/databasebackup/{obj.pk}/download/'
            )
        return '-'
    download_link.short_description = 'Téléchargement'
    
    def get_urls(self):
        """Ajouter les URLs personnalisées."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:backup_id>/download/',
                self.admin_site.admin_view(self.download_backup),
                name='core_databasebackup_download'
            ),
            path(
                'create-manual-backup/',
                self.admin_site.admin_view(self.create_manual_backup),
                name='core_databasebackup_manual'
            ),
        ]
        return custom_urls + urls
    
    def download_backup(self, request, backup_id):
        """Vue pour télécharger une sauvegarde."""
        backup = get_object_or_404(DatabaseBackup, pk=backup_id)
        
        # Vérifier que le fichier existe
        if not backup.file_exists:
            raise Http404("Le fichier de sauvegarde n'existe pas sur le disque.")
        
        # Vérifier que la sauvegarde est réussie
        if backup.status != 'success':
            messages.error(request, "Cette sauvegarde n'est pas dans un état valide pour le téléchargement.")
            return self.response_redirect(request, '../')
        
        try:
            # Lire le fichier
            file_path = Path(backup.file_path)
            
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{backup.filename}"'
                return response
                
        except Exception as e:
            messages.error(request, f"Erreur lors du téléchargement: {str(e)}")
            return self.response_redirect(request, '../')
    
    def create_manual_backup(self, request):
        """Vue pour déclencher une sauvegarde manuelle."""
        from apps.core.tasks import manual_backup_task
        
        try:
            # Déclencher la tâche Celery
            task = manual_backup_task.delay(user_id=request.user.id)
            
            messages.success(
                request, 
                f"Sauvegarde manuelle déclenchée. ID de tâche: {task.id}. "
                "Actualisez la page dans quelques minutes pour voir le résultat."
            )
            
        except Exception as e:
            messages.error(request, f"Erreur lors du déclenchement de la sauvegarde: {str(e)}")
        
        return self.response_redirect(request, '../')
    
    def response_redirect(self, request, url):
        """Redirection helper."""
        from django.shortcuts import redirect
        return redirect(url)
    
    def changelist_view(self, request, extra_context=None):
        """Ajouter le bouton de sauvegarde manuelle."""
        extra_context = extra_context or {}
        extra_context['show_manual_backup_button'] = True
        return super().changelist_view(request, extra_context)
