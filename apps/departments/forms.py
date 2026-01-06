"""
Formulaires pour le module Departments.
"""

from django import forms
from django.contrib.auth import get_user_model
from .models import Department
from apps.members.models import Member

User = get_user_model()


class DepartmentForm(forms.ModelForm):
    """
    Formulaire pour créer/modifier un département.
    """
    
    class Meta:
        model = Department
        fields = ['name', 'description', 'leader', 'site']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du département'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Description du département (optionnel)'
            }),
            'leader': forms.Select(attrs={
                'class': 'form-select'
            }),
            'site': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les utilisateurs pour ne montrer que ceux avec des rôles appropriés
        self.fields['leader'].queryset = User.objects.filter(
            is_active=True,
            role__in=['admin', 'secretariat', 'responsable_groupe', 'encadrant']
        ).order_by('first_name', 'last_name')
        
        # Rendre le leader optionnel
        self.fields['leader'].required = False
        self.fields['leader'].empty_label = "Aucun responsable"
        
        # Rendre le site optionnel
        self.fields['site'].required = False
        self.fields['site'].empty_label = "Aucun site spécifique"


class DepartmentMembersForm(forms.Form):
    """
    Formulaire pour gérer les membres d'un département.
    """
    members = forms.ModelMultipleChoiceField(
        queryset=Member.objects.filter(status=Member.Status.ACTIF),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        label="Membres du département"
    )
    
    def __init__(self, *args, **kwargs):
        department = kwargs.pop('department', None)
        super().__init__(*args, **kwargs)
        
        # Ordonner les membres par nom
        self.fields['members'].queryset = Member.objects.filter(
            status=Member.Status.ACTIF
        ).order_by('last_name', 'first_name')
        
        # Pré-sélectionner les membres actuels du département
        if department:
            self.fields['members'].initial = department.members.all()