from django import forms
from django.contrib.auth import get_user_model
from .models import DriverProfile, TransportRequest

User = get_user_model()


class DriverProfileForm(forms.ModelForm):
    """Formulaire pour créer/modifier un profil chauffeur."""
    
    class Meta:
        model = DriverProfile
        fields = [
            'user', 'vehicle_type', 'vehicle_model', 'license_plate',
            'capacity', 'zone', 'is_available', 'available_sunday',
            'available_week', 'notes'
        ]
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'vehicle_type': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_model': forms.TextInput(attrs={'class': 'form-control'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '20'}),
            'zone': forms.TextInput(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'available_sunday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'available_week': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les utilisateurs qui n'ont pas déjà un profil chauffeur
        existing_drivers = DriverProfile.objects.values_list('user_id', flat=True)
        if self.instance.pk:
            # En mode édition, inclure l'utilisateur actuel
            existing_drivers = existing_drivers.exclude(pk=self.instance.pk)
        
        self.fields['user'].queryset = User.objects.exclude(id__in=existing_drivers)
        
        # Rendre certains champs obligatoires
        self.fields['user'].required = True
        self.fields['vehicle_type'].required = True


class TransportRequestForm(forms.ModelForm):
    """Formulaire pour créer/modifier une demande de transport."""
    
    class Meta:
        model = TransportRequest
        fields = [
            'requester_name', 'requester_phone', 'requester_email', 'pickup_address',
            'event_date', 'event_time', 'event_name', 'passengers_count',
            'notes'
        ]
        widgets = {
            'requester_name': forms.TextInput(attrs={'class': 'form-control'}),
            'requester_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'requester_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'pickup_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'event_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'event_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'event_name': forms.TextInput(attrs={'class': 'form-control'}),
            'passengers_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '20'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre certains champs obligatoires
        self.fields['requester_name'].required = True
        self.fields['requester_phone'].required = True
        self.fields['pickup_address'].required = True
        self.fields['event_date'].required = True
        self.fields['event_time'].required = True


class DriverAssignmentForm(forms.ModelForm):
    """Formulaire pour assigner un chauffeur à une demande."""
    
    class Meta:
        model = TransportRequest
        fields = ['driver', 'status']
        widgets = {
            'driver': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les chauffeurs disponibles
        self.fields['driver'].queryset = DriverProfile.objects.filter(is_available=True)
        self.fields['driver'].empty_label = "Sélectionner un chauffeur"