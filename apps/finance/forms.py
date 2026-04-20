"""Formulaires pour le module Finance."""

from pathlib import Path

from django import forms

from apps.core.forms import EnhancedModelForm
from .models import FinancialTransaction, ReceiptProof, BudgetLine, FinanceCategory


class TransactionForm(EnhancedModelForm):
    """Formulaire de création/édition de transaction."""
    
    class Meta:
        model = FinancialTransaction
        fields = [
            'transaction_type', 'amount', 'transaction_date',
            'payment_method', 'category', 'description',
            'member', 'event', 'notes'
        ]
        widgets = {
            'amount': forms.NumberInput(attrs={
                'step': '0.01', 
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'transaction_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class ProofUploadForm(EnhancedModelForm):
    """Formulaire d'upload de justificatif."""
    
    class Meta:
        model = ReceiptProof
        fields = ['transaction', 'proof_type', 'image', 'notes']
        widgets = {
            'image': forms.FileInput(attrs={'accept': 'image/*'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class BudgetLineForm(EnhancedModelForm):
    """Formulaire de ligne budgétaire."""
    
    class Meta:
        model = BudgetLine
        fields = ['category', 'year', 'month', 'planned_amount', 'notes']
        widgets = {
            'year': forms.NumberInput(attrs={
                'min': 2020,
                'max': 2050
            }),
            'month': forms.NumberInput(attrs={
                'min': 1, 
                'max': 12
            }),
            'planned_amount': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0.00',
                'placeholder': '0.00'
            }),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class FinanceCategoryForm(EnhancedModelForm):
    """Formulaire de catégorie financière."""
    
    class Meta:
        model = FinanceCategory
        fields = ['name', 'description', 'is_income', 'budget_annual', 'parent', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Nom de la catégorie'}),
            'description': forms.Textarea(attrs={'rows': 2}),
            'budget_annual': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
        labels = {
            'is_income': 'Catégorie de recettes (cocher si c\'est une entrée d\'argent)',
        }


class FinanceExcelImportForm(forms.Form):
    """Import Excel structure pour le module finance."""

    file = forms.FileField(
        label='Classeur Excel',
        help_text='Formats acceptés : .xlsx, .xlsm',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xlsm',
        }),
    )
    dry_run = forms.BooleanField(
        label='Simulation uniquement',
        required=False,
        help_text='Vérifie le classeur sans enregistrer les données.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data['file']
        extension = Path(uploaded_file.name).suffix.lower()
        if extension not in {'.xlsx', '.xlsm'}:
            raise forms.ValidationError('Utilisez un fichier Excel au format .xlsx ou .xlsm.')
        if uploaded_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError('Le fichier ne doit pas dépasser 10 Mo.')
        return uploaded_file


class DonationReceiptForm(forms.Form):
    """Formulaire de génération de reçu de don (espèces, chèque…)."""

    DONATION_TYPE_CHOICES = [
        ('don', 'Don'),
        ('dime', 'Dîme'),
        ('offrande', 'Offrande'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('especes', 'Espèces'),
        ('cheque', 'Chèque'),
        ('virement', 'Virement bancaire'),
        ('carte', 'Carte bancaire'),
        ('mobile', 'Paiement mobile'),
        ('autre', 'Autre'),
    ]

    member = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label='Membre',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Sélectionnez un membre pour pré-remplir les informations.',
    )
    donor_name = forms.CharField(
        max_length=200,
        label='Nom du donateur',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom et prénom'}),
    )
    donor_address = forms.CharField(
        required=False,
        label='Adresse',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Adresse complète'}),
    )
    donor_email = forms.EmailField(
        required=False,
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemple.com'}),
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        label='Montant (€)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': '0.00'}),
    )
    donation_type = forms.ChoiceField(
        choices=DONATION_TYPE_CHOICES,
        label='Type',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        label='Mode de paiement',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    donation_date = forms.DateField(
        label='Date du don',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.members.models import Member
        self.fields['member'].queryset = Member.objects.filter(
            status='actif'
        ).order_by('last_name', 'first_name')
