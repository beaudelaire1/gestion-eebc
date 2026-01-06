from django import forms
from django.core.exceptions import ValidationError
from .models import Child, BibleClass, AgeGroup
from apps.transport.models import DriverProfile


class ChildForm(forms.ModelForm):
    """
    Formulaire pour créer/modifier un enfant du club biblique.
    """
    
    class Meta:
        model = Child
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 'photo',
            'bible_class', 'father_name', 'father_phone', 'father_email',
            'mother_name', 'mother_phone', 'mother_email',
            'emergency_contact', 'emergency_phone', 'allergies', 'medical_notes',
            'needs_transport', 'pickup_address', 'assigned_driver', 'notes'
        ]
        
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom de l\'enfant'
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
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'bible_class': forms.Select(attrs={
                'class': 'form-select'
            }),
            'father_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom complet du père'
            }),
            'father_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0694123456'
            }),
            'father_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemple.com'
            }),
            'mother_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom complet de la mère'
            }),
            'mother_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0694123456'
            }),
            'mother_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemple.com'
            }),
            'emergency_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du contact d\'urgence'
            }),
            'emergency_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0694123456'
            }),
            'allergies': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Allergies connues...'
            }),
            'medical_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes médicales importantes...'
            }),
            'needs_transport': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'pickup_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Adresse de ramassage...'
            }),
            'assigned_driver': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes diverses...'
            })
        }
        
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'date_of_birth': 'Date de naissance',
            'gender': 'Genre',
            'photo': 'Photo',
            'bible_class': 'Classe',
            'father_name': 'Nom du père',
            'father_phone': 'Téléphone du père',
            'father_email': 'Email du père',
            'mother_name': 'Nom de la mère',
            'mother_phone': 'Téléphone de la mère',
            'mother_email': 'Email de la mère',
            'emergency_contact': 'Contact d\'urgence',
            'emergency_phone': 'Téléphone d\'urgence',
            'allergies': 'Allergies',
            'medical_notes': 'Notes médicales',
            'needs_transport': 'Besoin de transport',
            'pickup_address': 'Adresse de ramassage',
            'assigned_driver': 'Chauffeur assigné',
            'notes': 'Notes'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les classes actives
        self.fields['bible_class'].queryset = BibleClass.objects.filter(is_active=True)
        self.fields['bible_class'].empty_label = "Sélectionner une classe"
        
        # Filtrer les chauffeurs actifs
        try:
            self.fields['assigned_driver'].queryset = DriverProfile.objects.filter(is_active=True)
            self.fields['assigned_driver'].empty_label = "Aucun chauffeur"
        except:
            # Si le modèle DriverProfile n'existe pas encore
            self.fields['assigned_driver'].widget = forms.HiddenInput()
        
        # Champs obligatoires
        required_fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'father_name', 'father_phone']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
                self.fields[field_name].widget.attrs['required'] = True
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validation du transport
        needs_transport = cleaned_data.get('needs_transport')
        pickup_address = cleaned_data.get('pickup_address')
        
        if needs_transport and not pickup_address:
            raise ValidationError({
                'pickup_address': 'L\'adresse de ramassage est obligatoire si l\'enfant a besoin de transport.'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Assigner automatiquement à une classe selon l'âge si pas de classe sélectionnée
        if not instance.bible_class and instance.date_of_birth:
            age = instance.age
            age_group = AgeGroup.objects.filter(
                min_age__lte=age,
                max_age__gte=age
            ).first()
            
            if age_group:
                bible_class = BibleClass.objects.filter(
                    age_group=age_group,
                    is_active=True
                ).first()
                
                if bible_class:
                    instance.bible_class = bible_class
        
        if commit:
            instance.save()
        
        return instance


class ChildSearchForm(forms.Form):
    """
    Formulaire de recherche pour les enfants.
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom, prénom ou nom des parents...'
        })
    )
    
    bible_class = forms.ModelChoiceField(
        queryset=BibleClass.objects.filter(is_active=True),
        required=False,
        empty_label="Toutes les classes",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    needs_transport = forms.ChoiceField(
        choices=[
            ('', 'Tous'),
            ('yes', 'Avec transport'),
            ('no', 'Sans transport')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    is_active = forms.ChoiceField(
        choices=[
            ('', 'Tous'),
            ('yes', 'Actifs'),
            ('no', 'Inactifs')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )