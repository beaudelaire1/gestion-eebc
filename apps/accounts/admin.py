from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from django.utils.html import format_html

from apps.core.models import AuditLog
from apps.core.security import can_manage_account
from .models import User
from .two_factor_policy import requires_2fa_enrollment
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
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'get_role_display', 'is_active', 'two_factor_state',
    ]
    list_filter = ['is_active', 'is_staff', 'date_joined', 'two_factor_enabled']
    actions = ['reset_two_factor']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering = ['last_name', 'first_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations EEBC', {
            'fields': ('roles', 'phone', 'photo', 'date_joined_church')
        }),
        ('Double authentification', {
            'fields': ('two_factor_state', 'two_factor_help'),
            'description': (
                "Le secret TOTP et les codes de secours ne sont pas modifiables "
                "à la main : utilisez l'action « Réinitialiser la double "
                "authentification » depuis la liste des utilisateurs."
            ),
        }),
    )

    readonly_fields = ('two_factor_state', 'two_factor_help')

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations EEBC', {
            'fields': ('roles', 'phone', 'first_name', 'last_name', 'email')
        }),
    )

    def get_role_display(self, obj):
        """Affiche les rôles dans la liste."""
        return obj.get_role_display()
    get_role_display.short_description = 'Rôles'

    @admin.display(description='2FA')
    def two_factor_state(self, obj):
        """État lisible en un coup d'œil, y compris la configuration inachevée.

        Un compte qui possède un secret sans avoir confirmé a flashé le QR code
        sans jamais saisir le code : son application affiche des codes EEBC, il
        se croit protégé, mais la connexion ne les demande pas. C'est
        exactement l'appel que reçoit le support, donc l'admin doit le montrer.
        """
        if obj.two_factor_enabled:
            colour, label = '#198754', '✔ Activée'
        elif (obj.two_factor_secret or '').strip():
            colour, label = '#fd7e14', '⚠ Configuration inachevée'
        elif requires_2fa_enrollment(obj):
            colour, label = '#dc3545', '✗ Absente (obligatoire)'
        else:
            colour, label = '#6c757d', '✗ Absente'

        return format_html('<span style="color:{};">{}</span>', colour, label)

    @admin.display(description='Conséquence')
    def two_factor_help(self, obj):
        if requires_2fa_enrollment(obj):
            return (
                "Ce compte porte un rôle privilégié : il est redirigé vers la "
                "page de configuration tant qu'il n'a pas enrôlé un second "
                "facteur."
            )
        return "La double authentification est facultative pour ce compte."

    @admin.action(description="Réinitialiser la double authentification")
    def reset_two_factor(self, request, queryset):
        """Rendre son accès à quelqu'un qui a perdu ou changé de téléphone.

        Le secret et les codes de secours sont effacés : le compte reflashe un
        QR code neuf à la prochaine connexion. Un compte privilégié y est
        d'ailleurs contraint avant de pouvoir rouvrir quoi que ce soit.
        """
        reset_count = 0
        refused = []

        for user in queryset:
            # Retirer le second facteur d'un compte privilégié est un geste
            # sensible : seul un administrateur peut viser une telle cible.
            if not can_manage_account(request.user, user):
                refused.append(user.username)
                continue

            if not user.two_factor_enabled and not (user.two_factor_secret or '').strip():
                continue

            user.disable_two_factor()
            reset_count += 1

            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.UPDATE,
                model_name='User',
                object_id=str(user.pk),
                object_repr=user.username,
                changes={'two_factor': 'reset'},
                path=request.path,
                extra_data={'reason': 'admin_two_factor_reset'},
            )

        if reset_count:
            self.message_user(
                request,
                f"Double authentification réinitialisée pour {reset_count} compte(s). "
                "Ils devront flasher un nouveau QR code.",
                messages.SUCCESS,
            )
        elif not refused:
            self.message_user(
                request,
                "Aucun des comptes sélectionnés n'avait de double authentification "
                "à réinitialiser.",
                messages.INFO,
            )

        if refused:
            self.message_user(
                request,
                "Seul un administrateur peut réinitialiser un compte privilégié. "
                f"Comptes ignorés : {', '.join(refused)}.",
                messages.WARNING,
            )
