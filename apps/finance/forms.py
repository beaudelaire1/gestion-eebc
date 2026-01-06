"""Formulaires pour le module Finance."""

from django import forms
from apps.core.forms import EnhancedModelForm
from .models import FinancialTransaction, ReceiptProof, BudgetLine


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
