from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.core.forms import EnhancedForm
from apps.core.validators import phone_validator
from .widgets import MultipleRoleField

User = get_user_model()


class UserCreationByTeamForm(EnhancedForm):
    """Formulaire de création d'utilisateur par l'équipe."""
    
    first_name = forms.CharField(
        max_length=150,
        min_length=2,
        label="Prénom",
        widget=forms.TextInput(attrs={
            'placeholder': 'Prénom'
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        min_length=2,
        label="Nom",
        widget=forms.TextInput(attrs={
            'placeholder': 'Nom de famille'
        })
    )
    
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'placeholder': 'email@exemple.com'
        })
    )
    
    phone = forms.CharField(
        max_length=20,
        min_length=10,
        required=False,
        label="Téléphone",
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            'placeholder': '0694 XX XX XX'
        })
    )
    
    roles = MultipleRoleField(
        label="Rôles",
        help_text="Sélectionnez un ou plusieurs rôles pour cet utilisateur",
        required=True
    )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("Un utilisateur avec cette adresse email existe déjà. Veuillez en choisir une autre.")
        return email
    
    def clean_first_name(self):
        first_name = self.cleaned_data['first_name'].strip()
        if not first_name:
            raise ValidationError("Le prénom est obligatoire.")
        if len(first_name) < 2:
            raise ValidationError("Le prénom doit contenir au moins 2 caractères.")
        return first_name.title()
    
    def clean_last_name(self):
        last_name = self.cleaned_data['last_name'].strip()
        if not last_name:
            raise ValidationError("Le nom de famille est obligatoire.")
        if len(last_name) < 2:
            raise ValidationError("Le nom de famille doit contenir au moins 2 caractères.")
        return last_name.upper()
    
    def clean_roles(self):
        roles = self.cleaned_data.get('roles', [])
        if not roles:
            raise ValidationError("Au moins un rôle doit être sélectionné.")
        return roles


class UserBulkImportForm(EnhancedForm):
    """Formulaire d'import en masse d'utilisateurs depuis Excel/CSV."""

    file = forms.FileField(
        label="Fichier Excel ou CSV",
        help_text="Formats acceptés : .xlsx, .xls, .csv. Colonnes requises : prénom, nom, email.",
        widget=forms.ClearableFileInput(attrs={
            'accept': '.xlsx,.xls,.csv',
        }),
    )

    default_roles = MultipleRoleField(
        label="Rôle(s) par défaut",
        help_text="Appliqué uniquement aux lignes sans colonne « rôle ».",
        required=False,
    )

    send_email = forms.BooleanField(
        label="Envoyer l'email d'invitation à chaque utilisateur",
        required=False,
        initial=True,
    )

    def clean_file(self):
        f = self.cleaned_data['file']
        name = (f.name or '').lower()
        if not name.endswith(('.xlsx', '.xls', '.csv', '.xlsm')):
            raise ValidationError("Format non supporté. Utilisez .xlsx, .xls ou .csv.")
        # Limite 5 Mo
        if f.size > 5 * 1024 * 1024:
            raise ValidationError("Fichier trop volumineux (max 5 Mo).")
        return f

    def clean_default_roles(self):
        return self.cleaned_data.get('default_roles') or ['membre']


class FirstLoginPasswordChangeForm(EnhancedForm):
    """Formulaire de changement de mot de passe à la première connexion."""
    
    new_password1 = forms.CharField(
        label="Nouveau mot de passe",
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Nouveau mot de passe'
        }),
        help_text="Votre mot de passe doit contenir au moins 8 caractères."
    )
    
    new_password2 = forms.CharField(
        label="Confirmer le mot de passe",
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirmer le mot de passe'
        })
    )
    
    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        if password:
            try:
                validate_password(password)
            except ValidationError as error:
                raise ValidationError(error.messages)
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError("Les deux mots de passe ne correspondent pas. Veuillez les saisir à nouveau.")
        
        return cleaned_data


class ProfileForm(forms.ModelForm):
    """Formulaire de mise à jour du profil utilisateur."""

    phone = forms.CharField(
        max_length=20,
        min_length=10,
        required=False,
        label="Téléphone",
        validators=[phone_validator],
        widget=forms.TextInput(attrs={'placeholder': '0694 XX XX XX'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Prénom'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Nom de famille'}),
            'email': forms.EmailInput(attrs={'placeholder': 'email@exemple.com'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Un autre utilisateur utilise déjà cette adresse email.")
        return email

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name'].strip()
        if not first_name:
            raise ValidationError("Le prénom est obligatoire.")
        return first_name.title()

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name'].strip()
        if not last_name:
            raise ValidationError("Le nom de famille est obligatoire.")
        return last_name.upper()