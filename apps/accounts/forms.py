from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()


class UserCreationByTeamForm(forms.Form):
    """Formulaire de création d'utilisateur par l'équipe."""
    
    first_name = forms.CharField(
        max_length=150,
        label="Prénom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prénom'
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        label="Nom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom de famille'
        })
    )
    
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@exemple.com'
        })
    )
    
    phone = forms.CharField(
        max_length=20,
        required=False,
        label="Téléphone",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0694 XX XX XX'
        })
    )
    
    role = forms.ChoiceField(
        choices=User.Role.choices,
        label="Rôle",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("Un utilisateur avec cet email existe déjà.")
        return email
    
    def clean_first_name(self):
        first_name = self.cleaned_data['first_name'].strip()
        if not first_name:
            raise ValidationError("Le prénom est obligatoire.")
        return first_name.title()
    
    def clean_last_name(self):
        last_name = self.cleaned_data['last_name'].strip()
        if not last_name:
            raise ValidationError("Le nom est obligatoire.")
        return last_name.upper()


class FirstLoginPasswordChangeForm(forms.Form):
    """Formulaire de changement de mot de passe à la première connexion."""
    
    new_password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nouveau mot de passe'
        }),
        help_text="Votre mot de passe doit contenir au moins 8 caractères."
    )
    
    new_password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
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
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("Les deux mots de passe ne correspondent pas.")
        
        return cleaned_data