from django.contrib import admin
from .models import DocumentCategory, Document, DocumentShare, DocumentAccess


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'color', 'order', 'document_count']
    list_editable = ['order']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

    def document_count(self, obj):
        return obj.documents.count()
    document_count.short_description = "Documents"


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'media_type', 'category', 'source', 'file_size_display', 'is_confidential', 'uploaded_by', 'created_at']
    list_filter = ['media_type', 'source', 'is_confidential', 'category', 'created_at']
    search_fields = ['title', 'description', 'file_name', 'tags']
    readonly_fields = ['file_name', 'file_size', 'file_type', 'media_type', 'created_at', 'updated_at']
    raw_id_fields = ['linked_member', 'uploaded_by']
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'file', 'category', 'source', 'tags')
        }),
        ('Métadonnées fichier', {
            'fields': ('file_name', 'file_size', 'file_type', 'media_type'),
            'classes': ('collapse',),
        }),
        ('Liaison', {
            'fields': ('linked_member', 'linked_app', 'linked_object_id'),
            'classes': ('collapse',),
        }),
        ('Sécurité', {
            'fields': ('is_confidential', 'uploaded_by'),
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(DocumentShare)
class DocumentShareAdmin(admin.ModelAdmin):
    list_display = ['document', 'recipient_email', 'shared_by', 'shared_at', 'expires_at', 'accessed_at']
    list_filter = ['shared_at']
    search_fields = ['recipient_email', 'recipient_name', 'document__title']
    readonly_fields = ['share_token', 'shared_at']


@admin.register(DocumentAccess)
class DocumentAccessAdmin(admin.ModelAdmin):
    list_display = ['document', 'user', 'action', 'ip_address', 'accessed_at']
    list_filter = ['action', 'accessed_at']
    search_fields = ['document__title']
    readonly_fields = ['accessed_at']
