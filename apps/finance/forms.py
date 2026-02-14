"""Formulaires pour le module Finance."""

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
