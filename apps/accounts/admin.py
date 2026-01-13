from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from .models import User
from .widgets import MultipleRoleField


class UserAdminForm(forms.ModelForm):
    """Formulaire personnalisé pour l'admin des utilisateurs."""
    
    roles = MultipleRoleField(
        label="Rôles",
        help_text="Sélectionnez un ou plusieurs rôles pour cet utilisateur",
        required=False
    )
    
    class Meta:
        model = User
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Pré-remplir le champ roles avec les rôles actuels
            self.fields['roles'].initial = self.instance.get_roles_list()
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Convertir la liste de rôles en chaîne
        roles = self.cleaned_data.get('roles', [])
        user.role = ','.join(roles) if roles else User.Role.MEMBRE
        if commit:
            user.save()
        return user


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminForm
    list_display = ['username', 'email', 'first_name', 'last_name', 'get_role_display', 'is_active']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering = ['last_name', 'first_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations EEBC', {
            'fields': ('roles', 'phone', 'photo', 'date_joined_church')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations EEBC', {
            'fields': ('roles', 'phone', 'first_name', 'last_name', 'email')
        }),
    )
    
    def get_role_display(self, obj):
        """Affiche les rôles dans la liste."""
        return obj.get_role_display()
    get_role_display.short_description = 'Rôles'

