from django.contrib import admin
from .models import ImportLog


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'import_type', 'status', 'total_rows', 'success_rows', 'error_rows', 'imported_by', 'started_at']
    list_filter = ['import_type', 'status', 'started_at']
    search_fields = ['file_name', 'imported_by__username']
    readonly_fields = ['started_at', 'completed_at', 'duration', 'success_rate']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('import_type', 'file_name', 'file_path', 'imported_by')
        }),
        ('Statut', {
            'fields': ('status', 'started_at', 'completed_at', 'duration')
        }),
        ('Statistiques', {
            'fields': ('total_rows', 'processed_rows', 'success_rows', 'error_rows', 'success_rate')
        }),
        ('Logs', {
            'fields': ('success_log', 'error_log'),
            'classes': ('collapse',)
        }),
    )
    
    def duration(self, obj):
        return obj.duration
    duration.short_description = 'Durée'
    
    def success_rate(self, obj):
        return f"{obj.success_rate:.1f}%"
    success_rate.short_description = 'Taux de réussite'