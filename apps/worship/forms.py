"""Formulaires pour le module Worship."""

from django import forms
from .models import WorshipService, ServiceRole, ServicePlanItem


class WorshipServiceForm(forms.ModelForm):
    """Formulaire de création/édition de service."""
    
    class Meta:
        model = WorshipService
        fields = [
            'event', 'service_type', 'theme', 'bible_text',
            'sermon_title', 'sermon_notes', 'expected_attendance', 'notes'
        ]
        widgets = {
            'sermon_notes': forms.Textarea(attrs={'rows': 4}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class ServiceRoleForm(forms.ModelForm):
    """Formulaire d'assignation de rôle."""
    
    class Meta:
        model = ServiceRole
        fields = ['role', 'member', 'user', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class ServicePlanItemForm(forms.ModelForm):
    """Formulaire d'élément de programme."""
    
    class Meta:
        model = ServicePlanItem
        fields = [
            'item_type', 'title', 'start_time', 'duration_minutes',
            'responsible', 'notes', 'resources_needed'
        ]
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
            'resources_needed': forms.Textarea(attrs={'rows': 2}),
        }
