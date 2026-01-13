"""
Formulaires pour l'app membres.
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import Member, LifeEvent, VisitationLog
from apps.core.models import Site, Family


class MemberForm(forms.ModelForm):
    """Formulaire pour créer/modifier un membre."""
    
    class Meta:
        model = Member
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender',
            'email', 'phone', 'address', 'city', 'postal_code',
            'family', 'family_role', 'marital_status', 'profession',
            'site', 'status', 'is_baptized', 'baptism_date',
            'wedding_date', 'photo', 'notes',
            'notify_by_email', 'notify_by_sms', 'notify_by_whatsapp', 'whatsapp_number'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de famille'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemple.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+33 1 23 45 67 89'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Adresse complète'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Code postal'
            }),
            'family': forms.Select(attrs={
                'class': 'form-select'
            }),
            'family_role': forms.Select(attrs={
                'class': 'form-select'
            }),
            'marital_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'profession': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Profession'
            }),
            'site': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'baptism_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'wedding_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes personnelles...'
            }),
            'whatsapp_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+33 1 23 45 67 89'
            }),
            'notify_by_email': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notify_by_sms': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notify_by_whatsapp': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_baptized': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Rendre certains champs optionnels
        self.fields['family'].required = False
        self.fields['site'].required = False
        self.fields['date_of_birth'].required = False
        self.fields['baptism_date'].required = False
        self.fields['wedding_date'].required = False
        self.fields['gender'].required = False
        
        # Ajouter des choix vides
        self.fields['family'].empty_label = "Aucune famille"
        self.fields['site'].empty_label = "Sélectionner un site"
        self.fields['gender'].empty_label = "Non spécifié"
        
        # Filtrer les familles actives
        self.fields['family'].queryset = Family.objects.filter(is_active=True)
        
        # Filtrer les sites actifs
        self.fields['site'].queryset = Site.objects.filter(is_active=True)
    
    def clean_email(self):
        """Valider l'unicité de l'email."""
        email = self.cleaned_data.get('email')
        if email:
            # Vérifier l'unicité sauf pour l'instance actuelle
            qs = Member.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise ValidationError("Un membre avec cet email existe déjà.")
        
        return email
    
    def clean(self):
        """Validation globale du formulaire."""
        cleaned_data = super().clean()
        
        # Vérifier que la date de baptême n'est pas antérieure à la naissance
        birth_date = cleaned_data.get('date_of_birth')
        baptism_date = cleaned_data.get('baptism_date')
        
        if birth_date and baptism_date and baptism_date < birth_date:
            raise ValidationError("La date de baptême ne peut pas être antérieure à la date de naissance.")
        
        # Si baptisé, la date de baptême est requise
        is_baptized = cleaned_data.get('is_baptized')
        if is_baptized and not baptism_date:
            self.add_error('baptism_date', "La date de baptême est requise si le membre est baptisé.")
        
        # Vérifier le numéro WhatsApp si les notifications WhatsApp sont activées
        notify_whatsapp = cleaned_data.get('notify_by_whatsapp')
        whatsapp_number = cleaned_data.get('whatsapp_number')
        
        if notify_whatsapp and not whatsapp_number:
            self.add_error('whatsapp_number', "Le numéro WhatsApp est requis si les notifications WhatsApp sont activées.")
        
        return cleaned_data


class LifeEventForm(forms.ModelForm):
    """Formulaire pour les événements de vie."""
    
    class Meta:
        model = LifeEvent
        fields = [
            'event_type', 'title', 'event_date', 'priority',
            'primary_member', 'related_members', 'description',
            'requires_visit', 'announce_sunday', 'notes'
        ]
        widgets = {
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'event_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'primary_member': forms.Select(attrs={'class': 'form-select'}),
            'related_members': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'requires_visit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'announce_sunday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['related_members'].required = False
        self.fields['notes'].required = False


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
            'member': forms.Select(attrs={'class': 'form-select'}),
            'visitor': forms.Select(attrs={'class': 'form-select'}),
            'visit_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'visit_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'life_event': forms.Select(attrs={'class': 'form-select'}),
            'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'prayer_requests': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'follow_up_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'follow_up_needed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_confidential': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['visitor'].required = False
        self.fields['visit_date'].required = False
        self.fields['duration_minutes'].required = False
        self.fields['life_event'].required = False
        self.fields['prayer_requests'].required = False
        self.fields['follow_up_notes'].required = False
        
        # Filtrer les événements de vie non visités
        self.fields['life_event'].queryset = LifeEvent.objects.filter(
            requires_visit=True, 
            visit_completed=False
        )
        self.fields['life_event'].empty_label = "Aucun événement lié"