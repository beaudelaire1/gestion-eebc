from django.contrib import admin
from django import forms
from .models import Notification, EmailLog, SMSLog, Announcement, EmailTemplate
from apps.core.widgets import TinyMCEWidget


class AnnouncementAdminForm(forms.ModelForm):
    """Formulaire admin avec TinyMCE pour les annonces."""
    class Meta:
        model = Announcement
        fields = '__all__'
        widgets = {
            'content': TinyMCEWidget(config={'height': 300}),
        }


class EmailTemplateAdminForm(forms.ModelForm):
    """Formulaire admin avec TinyMCE pour les templates d'emails."""
    class Meta:
        model = EmailTemplate
        fields = '__all__'
        widgets = {
            'html_content': TinyMCEWidget(config={
                'height': 400,
                'plugins': 'link image code table lists',
                'toolbar': 'undo redo | formatselect | bold italic | alignleft aligncenter alignright | bullist numlist | link image | code'
            }),
            'text_content': forms.Textarea(attrs={'rows': 10}),
            'variables_help': forms.Textarea(attrs={'rows': 5}),
        }


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'read_at']


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['subject', 'recipient_email', 'recipient_name', 'status', 'sent_at', 'created_at']
    list_filter = ['status', 'created_at', 'sent_at']
    search_fields = ['subject', 'recipient_email', 'recipient_name', 'body']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'sent_at']
    
    fieldsets = (
        ('Destinataire', {
            'fields': ('recipient_email', 'recipient_name')
        }),
        ('Contenu', {
            'fields': ('subject', 'body')
        }),
        ('Statut', {
            'fields': ('status', 'error_message')
        }),
        ('Horodatage', {
            'fields': ('created_at', 'sent_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimiser les requêtes."""
        return super().get_queryset(request).select_related()
    
    def has_add_permission(self, request):
        """Empêcher l'ajout manuel de logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Empêcher la modification des logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Permettre la suppression pour le nettoyage."""
        return request.user.is_superuser
    
    actions = ['mark_as_failed', 'export_failed_emails']
    
    def mark_as_failed(self, request, queryset):
        """Marquer les emails sélectionnés comme échoués."""
        updated = queryset.filter(status='pending').update(
            status='failed',
            error_message='Marqué comme échoué manuellement'
        )
        self.message_user(
            request,
            f'{updated} email(s) marqué(s) comme échoué(s).'
        )
    mark_as_failed.short_description = "Marquer comme échoué"
    
    def export_failed_emails(self, request, queryset):
        """Exporter les emails échoués pour analyse."""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="emails_echoues.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Email', 'Nom', 'Sujet', 'Erreur', 'Date création'])
        
        for log in queryset.filter(status='failed'):
            writer.writerow([
                log.recipient_email,
                log.recipient_name,
                log.subject,
                log.error_message,
                log.created_at.strftime('%d/%m/%Y %H:%M')
            ])
        
        return response
    export_failed_emails.short_description = "Exporter les emails échoués"


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['recipient_phone', 'recipient_name', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['recipient_phone', 'recipient_name', 'message']
    date_hierarchy = 'created_at'


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    form = EmailTemplateAdminForm
    list_display = ['name', 'template_type', 'is_active', 'is_default', 'updated_at']
    list_filter = ['template_type', 'is_active', 'is_default']
    search_fields = ['name', 'subject']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'template_type', 'is_active', 'is_default')
        }),
        ('Contenu de l\'email', {
            'fields': ('subject', 'html_content', 'text_content')
        }),
        ('Aide et documentation', {
            'fields': ('variables_help',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Ajouter l'aide contextuelle selon le type de template
        if obj and obj.template_type:
            help_text = self._get_variables_help(obj.template_type)
            if help_text:
                form.base_fields['variables_help'].initial = help_text
        
        return form
    
    def _get_variables_help(self, template_type):
        """Retourne l'aide sur les variables selon le type de template."""
        help_texts = {
            'event_notification': """
Variables disponibles pour les notifications d'événements:
- {{event.title}} : Titre de l'événement
- {{event.description}} : Description de l'événement
- {{event.start_date}} : Date de début
- {{event.start_time}} : Heure de début
- {{event.location}} : Lieu de l'événement
- {{recipient_name}} : Nom du destinataire
- {{site_name}} : Nom du site
- {{site_url}} : URL du site
- {{current_year}} : Année actuelle
            """,
            'event_reminder': """
Variables disponibles pour les rappels d'événements:
- {{event.title}} : Titre de l'événement
- {{event.start_date}} : Date de début
- {{event.start_time}} : Heure de début
- {{event.location}} : Lieu de l'événement
- {{days_before}} : Nombre de jours avant l'événement
- {{is_today}} : True si l'événement est aujourd'hui
- {{is_tomorrow}} : True si l'événement est demain
- {{recipient_name}} : Nom du destinataire
            """,
            'transport_confirmation': """
Variables disponibles pour les confirmations de transport:
- {{transport_request.destination}} : Destination
- {{transport_request.pickup_location}} : Lieu de prise en charge
- {{transport_request.pickup_time}} : Heure de prise en charge
- {{transport_request.date}} : Date du transport
- {{driver.name}} : Nom du chauffeur (si assigné)
- {{driver.phone}} : Téléphone du chauffeur (si assigné)
- {{has_driver}} : True si un chauffeur est assigné
- {{recipient_name}} : Nom du passager
            """,
        }
        
        return help_texts.get(template_type, "")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    form = AnnouncementAdminForm
    list_display = ['title', 'created_by', 'is_active', 'is_pinned', 'start_date', 'end_date']
    list_filter = ['is_active', 'is_pinned']
    search_fields = ['title', 'content']
    date_hierarchy = 'created_at'
    
    class Media:
        js = ('https://cdn.jsdelivr.net/npm/tinymce@6/tinymce.min.js',)

