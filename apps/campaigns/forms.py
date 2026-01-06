from django import forms
from django.core.exceptions import ValidationError
from .models import Campaign, Donation


class CampaignForm(forms.ModelForm):
    """Formulaire pour créer/modifier une campagne."""
    
    class Meta:
        model = Campaign
        fields = [
            'name', 'description', 'goal_amount', 'start_date', 
            'end_date', 'responsible', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de la campagne'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Description de la campagne'
            }),
            'goal_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'responsible': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'name': 'Nom de la campagne',
            'description': 'Description',
            'goal_amount': 'Objectif (€)',
            'start_date': 'Date de début',
            'end_date': 'Date de fin',
            'responsible': 'Responsable',
            'is_active': 'Campagne active'
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        goal_amount = cleaned_data.get('goal_amount')
        
        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError(
                    "La date de fin doit être postérieure à la date de début."
                )
        
        if goal_amount and goal_amount <= 0:
            raise ValidationError(
                "L'objectif doit être supérieur à 0."
            )
        
        return cleaned_data


class DonationForm(forms.ModelForm):
    """Formulaire pour enregistrer un don."""
    
    class Meta:
        model = Donation
        fields = ['campaign', 'donor_name', 'is_anonymous', 'amount', 'notes']
        widgets = {
            'campaign': forms.Select(attrs={
                'class': 'form-select'
            }),
            'donor_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du donateur (optionnel si anonyme)'
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes sur le don (optionnel)'
            })
        }
        labels = {
            'campaign': 'Campagne',
            'donor_name': 'Nom du donateur',
            'is_anonymous': 'Don anonyme',
            'amount': 'Montant (€)',
            'notes': 'Notes'
        }
    
    def __init__(self, *args, **kwargs):
        campaign_id = kwargs.pop('campaign_id', None)
        super().__init__(*args, **kwargs)
        
        # Si une campagne est spécifiée, la présélectionner et masquer le champ
        if campaign_id:
            self.fields['campaign'].initial = campaign_id
            self.fields['campaign'].widget = forms.HiddenInput()
        
        # Filtrer les campagnes actives uniquement
        self.fields['campaign'].queryset = Campaign.objects.filter(is_active=True)
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError("Le montant doit être supérieur à 0.")
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        is_anonymous = cleaned_data.get('is_anonymous')
        donor_name = cleaned_data.get('donor_name')
        
        if not is_anonymous and not donor_name:
            raise ValidationError(
                "Veuillez spécifier le nom du donateur ou cocher 'Don anonyme'."
            )
        
        return cleaned_data