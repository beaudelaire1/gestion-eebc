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
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'transaction_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'member': forms.Select(attrs={'class': 'form-select'}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class ProofUploadForm(forms.ModelForm):
    """Formulaire d'upload de justificatif."""
    
    class Meta:
        model = ReceiptProof
        fields = ['transaction', 'proof_type', 'image', 'notes']
        widgets = {
            'transaction': forms.Select(attrs={'class': 'form-select'}),
            'proof_type': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class BudgetLineForm(forms.ModelForm):
    """Formulaire de ligne budgétaire."""
    
    class Meta:
        model = BudgetLine
        fields = ['category', 'year', 'month', 'planned_amount', 'notes']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'month': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '12'}),
            'planned_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
