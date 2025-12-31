from django.contrib import admin
from .models import Category, Equipment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'equipment_count']
    search_fields = ['name']
    
    def equipment_count(self, obj):
        return obj.equipment.count()
    equipment_count.short_description = "Équipements"


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'quantity', 'condition', 'location', 'responsible']
    list_filter = ['condition', 'category', 'location']
    search_fields = ['name', 'description', 'location']
    date_hierarchy = 'purchase_date'
    
    fieldsets = (
        ('Informations', {
            'fields': ('name', 'description', 'category', 'quantity', 'photo')
        }),
        ('État & Localisation', {
            'fields': ('condition', 'location', 'responsible')
        }),
        ('Achat', {
            'fields': ('purchase_date', 'purchase_price'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

