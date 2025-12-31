from django.contrib import admin
from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'leader', 'member_count', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    filter_horizontal = ['members']
    
    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = "Nombre de membres"

