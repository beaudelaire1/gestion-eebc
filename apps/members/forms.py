"""Formulaires pour le module Members et Pastoral CRM."""

from django import forms
from apps.core.forms import EnhancedModelForm
from apps.core.validators import (
    phone_validator, postal_code_validator, 
    validate_reasonable_birth_date, small_image_validator
)
from .models import Member, LifeEvent, VisitationLog


class MemberForm(EnhancedModelForm):
    """Formulaire de création/édition de membre."""
    
    # Redéfinir certains champs avec des validateurs personnalisés
    phone = forms.CharField(
        max_length=20,
        required=False,
        label="Téléphone",
        validators=[phone_validator]
    )
    
    postal_code = forms.CharField(
        max_length=5,
        required=False,
        label="Code postal",
        validators=[postal_code_validator]
    )
    
    date_of_birth = forms.DateField(
        required=False,
        label="Date de naissance",
        validators=[validate_reasonable_birth_date],
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    photo = forms.ImageField(
        required=False,
        label="Photo",
        validators=[small_image_validator],
        widget=forms.FileInput(attrs={'accept': 'image/*'})
    )
    
    class Meta:
        model = Member
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 'photo',
            'email', 'phone', 'address', 'city', 'postal_code',
            'marital_status', 'profession',
            'status', 'date_joined', 'is_baptized', 'baptism_date',
            'notes'
        ]
        widgets = {
            'date_joined': forms.DateInput(attrs={'type': 'date'}),
            'baptism_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class LifeEventForm(EnhancedModelForm):
    """Formulaire pour les événements de vie."""
    
    class Meta:
        model = LifeEvent
        fields = [
            'event_type', 'event_date', 'primary_member', 'related_members',
            'title', 'description', 'priority',
            'requires_visit', 'announce_sunday', 'notes'
        ]
        widgets = {
            'event_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'related_members': forms.SelectMultiple(attrs={'size': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['primary_member'].queryset = Member.objects.filter(status='actif').order_by('last_name')
        self.fields['related_members'].queryset = Member.objects.filter(status='actif').order_by('last_name')
        self.fields['related_members'].required = False


class VisitationLogForm(EnhancedModelForm):
    """Formulaire pour les visites pastorales."""
    
    class Meta:
        model = VisitationLog
        fields = [
            'member', 'visitor', 'visit_type', 'status',
            'scheduled_date', 'visit_date', 'duration_minutes',
            'life_event', 'summary', 'prayer_requests',
            'follow_up_needed', 'follow_up_notes', 'is_confidential'
        ]
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'visit_date': forms.DateInput(attrs={'type': 'date'}),
            'duration_minutes': forms.NumberInput(attrs={
                'placeholder': '45',
                'min': 5,
                'max': 300
            }),
            'summary': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Décrivez le déroulement de la visite...'
            }),
            'prayer_requests': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Sujets de prière mentionnés...'
            }),
            'follow_up_notes': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Actions à entreprendre...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Queryset pour les membres
        self.fields['member'].queryset = Member.objects.filter(status='actif').order_by('last_name', 'first_name')
        
        self.fields['visitor'].required = False
        self.fields['life_event'].required = False
