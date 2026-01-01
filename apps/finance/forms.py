"""Formulaires pour le module Finance."""

from django import forms
from .models import FinancialTransaction, ReceiptProof, BudgetLine


class TransactionForm(forms.ModelForm):
    """Formulaire de création/édition de transaction."""
    
    class Meta:
        model = FinancialTransaction
        fields = [
            'transaction_type', 'amount', 'transaction_date',
            'payment_method', 'category', 'description',
            'member', 'event', 'notes'
        ]
        widgets = {
            'transaction_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class ProofUploadForm(forms.ModelForm):
    """Formulaire d'upload de justificatif."""
    
    class Meta:
        model = ReceiptProof
        fields = ['proof_type', 'image', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class BudgetLineForm(forms.ModelForm):
    """Formulaire de ligne budgétaire."""
    
    class Meta:
        model = BudgetLine
        fields = ['category', 'year', 'month', 'planned_amount', 'notes']
