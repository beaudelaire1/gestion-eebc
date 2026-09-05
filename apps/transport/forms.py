from django import forms

from django.contrib.auth import get_user_model

from apps.core.security import is_ordinary_member
from apps.members.models import Member

from .models import DriverProfile, TransportRequest
from .requesters import member_profile, young_profile

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
            'request_type', 'requester_member',
            'requester_name', 'requester_phone', 'requester_email',
            'pickup_address', 'pickup_city', 'pickup_postal_code',
            'event_date', 'event_time', 'event_name', 'passengers_count',
            'notes'
        ]
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'requester_member': forms.Select(attrs={'class': 'form-select'}),
            'requester_name': forms.TextInput(attrs={'class': 'form-control'}),
            'requester_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'requester_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'pickup_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ex. 12 rue Schoelcher, lieu-dit / quartier',
            }),
            'pickup_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex. Cayenne',
            }),
            'pickup_postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex. 97300',
            }),
            'event_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'event_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'event_name': forms.TextInput(attrs={'class': 'form-control'}),
            'passengers_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '20'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        help_texts = {
            'pickup_address': "Numéro, rue, lieu-dit ou quartier — sans la ville ni le code postal.",
            'pickup_city': "Permet une localisation précise sur la carte.",
            'pickup_postal_code': "Code postal de la prise en charge (ex. 97300).",
        }

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_user = current_user
        self.forced_member = member_profile(current_user)
        self.forced_young = young_profile(current_user)

        # Rendre certains champs obligatoires
        self.fields['requester_name'].required = True
        self.fields['requester_phone'].required = True
        self.fields['pickup_address'].required = True
        self.fields['event_date'].required = True
        self.fields['event_time'].required = True
        self.fields['requester_member'].required = False
        self.fields['requester_member'].empty_label = "— Aucun —"

        # Préremplissage automatique pour un compte connecté (en création
        # uniquement). Un jeune non membre de l'église n'a pas de fiche membre :
        # sa fiche jeune décrit alors le demandeur.
        profile = self.forced_member or self.forced_young
        if profile is not None and not self.instance.pk:
            if self.forced_member is not None:
                self.fields['requester_member'].initial = self.forced_member.pk
            pickup = getattr(profile, 'pickup_address', '') or profile.address
            if not self.initial.get('requester_name'):
                self.initial['requester_name'] = profile.full_name
            if not self.initial.get('requester_phone') and profile.phone:
                self.initial['requester_phone'] = profile.phone
            if not self.initial.get('requester_email') and profile.email:
                self.initial['requester_email'] = profile.email
            if not self.initial.get('pickup_address') and pickup:
                self.initial['pickup_address'] = pickup
            if not self.initial.get('pickup_city') and getattr(profile, 'city', ''):
                self.initial['pickup_city'] = profile.city
            if not self.initial.get('pickup_postal_code') and getattr(profile, 'postal_code', ''):
                self.initial['pickup_postal_code'] = profile.postal_code
            if not self.initial.get('request_type'):
                self.initial['request_type'] = (
                    TransportRequest.RequestType.COVOITURAGE
                    if self.forced_member is not None
                    else TransportRequest.RequestType.CLUB
                )

        # Un membre ordinaire ne demande un transport que pour lui-même : le
        # sélecteur de membre exposerait l'annuaire complet et permettrait de
        # créer une demande au nom d'un autre membre.
        if is_ordinary_member(current_user):
            field = self.fields['requester_member']
            field.widget = forms.HiddenInput()
            field.queryset = (
                Member.objects.filter(pk=self.forced_member.pk)
                if self.forced_member is not None
                else Member.objects.none()
            )
            if self.is_bound:
                # Écraser la valeur postée : un champ caché reste modifiable
                # côté navigateur.
                self.data = self.data.copy()
                self.data[self.add_prefix('requester_member')] = (
                    str(self.forced_member.pk) if self.forced_member else ''
                )

    def clean_requester_member(self):
        """Ignorer toute valeur postée : le demandeur est imposé par la session."""
        if is_ordinary_member(self.current_user):
            return self.forced_member
        return self.cleaned_data.get('requester_member')

    def save(self, commit=True):
        """Rattacher la demande à la fiche jeune du demandeur connecté.

        ``requester_young`` n'est pas un champ du formulaire : l'exposer
        reviendrait à publier la liste des jeunes, dont des mineurs. Il n'est
        posé que pour la personne qui dépose sa propre demande.
        """
        if is_ordinary_member(self.current_user) and not self.instance.pk:
            self.instance.requester_young = self.forced_young
        return super().save(commit=commit)


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