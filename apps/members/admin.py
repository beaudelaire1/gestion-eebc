from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import Member


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
