"""Formulaires pour le module Members et Pastoral CRM."""

from django import forms
from .models import Member, LifeEvent, VisitationLog


class MemberForm(forms.ModelForm):
    """Formulaire de création/édition de membre."""
    
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
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'date_joined': forms.DateInput(attrs={'type': 'date'}),
            'baptism_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class LifeEventForm(forms.ModelForm):
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
            'related_members': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['primary_member'].queryset = Member.objects.filter(status='actif').order_by('last_name')
        self.fields['related_members'].queryset = Member.objects.filter(status='actif').order_by('last_name')
        self.fields['related_members'].required = False


class VisitationLogForm(forms.ModelForm):
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
            'summary': forms.Textarea(attrs={'rows': 4}),
            'prayer_requests': forms.Textarea(attrs={'rows': 3}),
            'follow_up_notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['member'].queryset = Member.objects.filter(status='actif').order_by('last_name')
        self.fields['visitor'].required = False
        self.fields['life_event'].required = False
