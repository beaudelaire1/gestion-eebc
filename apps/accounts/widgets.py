from django import forms
from django.forms.widgets import CheckboxSelectMultiple
from .models import User


class MultipleRoleWidget(CheckboxSelectMultiple):
    """Widget pour sélectionner plusieurs rôles."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = User.Role.choices
    
    def format_value(self, value):
        """Convertit la valeur stockée en liste pour l'affichage."""
        if isinstance(value, str):
            return [role.strip() for role in value.split(',') if role.strip()]
        return value or []
    
    def value_from_datadict(self, data, files, name):
        """Convertit les données du formulaire en chaîne séparée par des virgules."""
        values = super().value_from_datadict(data, files, name)
        if values:
            return ','.join(values)
        return User.Role.MEMBRE


class MultipleRoleField(forms.MultipleChoiceField):
    """Champ pour sélectionner plusieurs rôles."""
    
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = User.Role.choices
        kwargs['widget'] = MultipleRoleWidget()
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """Convertit la valeur en liste."""
        if isinstance(value, str):
            return [role.strip() for role in value.split(',') if role.strip()]
        return value or []
    
    def validate(self, value):
        """Valide que tous les rôles sélectionnés sont valides."""
        if value:
            valid_roles = [choice[0] for choice in User.Role.choices]
            for role in value:
                if role not in valid_roles:
                    raise forms.ValidationError(f'Rôle invalide: {role}')