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
