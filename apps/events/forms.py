"""
Formulaires pour la gestion des événements.
"""

from django import forms
from django.contrib.auth import get_user_model
from apps.core.forms import EnhancedModelForm, EnhancedForm
from .models import Event, EventCategory

User = get_user_model()


class EventForm(EnhancedModelForm):
    """Formulaire de création/modification d'événement."""
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'category', 'start_date', 'start_time',
            'end_date', 'end_time', 'all_day', 'location', 'address',
            'recurrence', 'recurrence_end_date', 'visibility', 'organizers',
            'department', 'group', 'notification_scope', 'notify_before', 'image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Titre de l\'événement'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Description de l\'événement'
            }),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'location': forms.TextInput(attrs={
                'placeholder': 'Lieu de l\'événement'
            }),
            'address': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Adresse complète'
            }),
            'recurrence_end_date': forms.DateInput(attrs={'type': 'date'}),
            'organizers': forms.SelectMultiple(attrs={'size': '4'}),
            'notify_before': forms.NumberInput(attrs={
                'min': '0',
                'max': '30',
                'placeholder': '7'
            }),
            'image': forms.FileInput(attrs={'accept': 'image/*'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personnaliser les querysets
        self.fields['organizers'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # Rendre certains champs optionnels plus clairs
        self.fields['end_date'].required = False
        self.fields['end_time'].required = False
        self.fields['recurrence_end_date'].required = False
        self.fields['image'].required = False
        
        # Ajouter des labels d'aide
        self.fields['all_day'].help_text = "Cocher si l'événement dure toute la journée"
        self.fields['recurrence'].help_text = "Fréquence de répétition de l'événement"
        self.fields['notify_before'].help_text = "Nombre de jours avant l'événement pour envoyer la notification"
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        all_day = cleaned_data.get('all_day')
        recurrence = cleaned_data.get('recurrence')
        recurrence_end_date = cleaned_data.get('recurrence_end_date')
        
        # Validation des dates
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("La date de fin ne peut pas être antérieure à la date de début.")
        
        # Validation des heures pour les événements non "toute la journée"
        if not all_day:
            if start_date and end_date and start_date == end_date:
                if start_time and end_time and end_time <= start_time:
                    raise forms.ValidationError("L'heure de fin doit être postérieure à l'heure de début.")
        
        # Validation de la récurrence
        if recurrence and recurrence != Event.RecurrenceType.NONE:
            if not recurrence_end_date:
                raise forms.ValidationError("Une date de fin de récurrence est requise pour les événements récurrents.")
            if recurrence_end_date and start_date and recurrence_end_date <= start_date:
                raise forms.ValidationError("La date de fin de récurrence doit être postérieure à la date de début.")
        
        return cleaned_data


class EventCancelForm(EnhancedForm):
    """Formulaire d'annulation d'événement."""
    
    reason = forms.CharField(
        label="Raison de l'annulation",
        max_length=500,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Expliquez brièvement la raison de l\'annulation...'
        }),
        required=False
    )
    
    notify_participants = forms.BooleanField(
        label="Notifier les participants inscrits",
        initial=True,
        required=False
    )


class EventDuplicateForm(EnhancedForm):
    """Formulaire de duplication d'événement."""
    
    new_start_date = forms.DateField(
        label="Nouvelle date de début",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    new_start_time = forms.TimeField(
        label="Nouvelle heure de début",
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    
    duplicate_title_suffix = forms.CharField(
        label="Suffixe du titre",
        initial=" (Copie)",
        max_length=50,
        widget=forms.TextInput(attrs={
            'placeholder': ' (Copie)'
        })
    )
    
    def __init__(self, *args, original_event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_event = original_event
        
        if original_event:
            # Pré-remplir avec les données de l'événement original
            if original_event.start_time:
                self.fields['new_start_time'].initial = original_event.start_time
            else:
                self.fields['new_start_time'].required = False
    
    def clean_new_start_date(self):
        new_start_date = self.cleaned_data.get('new_start_date')
        
        if new_start_date:
            from datetime import date
            if new_start_date < date.today():
                raise forms.ValidationError("La nouvelle date ne peut pas être dans le passé.")
        
        return new_start_date


class EventSearchForm(EnhancedForm):
    """Formulaire de recherche d'événements."""
    
    search = forms.CharField(
        label="Recherche",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Rechercher par titre, description ou lieu...'
        })
    )
    
    category = forms.ModelChoiceField(
        label="Catégorie",
        queryset=EventCategory.objects.all(),
        required=False,
        empty_label="Toutes les catégories"
    )
    
    start_date = forms.DateField(
        label="À partir du",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    end_date = forms.DateField(
        label="Jusqu'au",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    visibility = forms.ChoiceField(
        label="Visibilité",
        choices=[('', 'Toutes')] + Event.Visibility.choices,
        required=False
    )
    
    show_cancelled = forms.BooleanField(
        label="Inclure les événements annulés",
        required=False
    )