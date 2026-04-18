from django import forms
from .models import Document, DocumentCategory


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'description', 'file', 'category', 'source', 'tags', 'is_confidential']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre du document',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description optionnelle...',
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '*/*',
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'tag1, tag2, tag3...',
            }),
            'is_confidential': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DocumentEditForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'description', 'category', 'source', 'tags', 'is_confidential']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'tag1, tag2, tag3...'}),
            'is_confidential': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DocumentShareForm(forms.Form):
    recipient_email = forms.EmailField(
        label="Email du destinataire",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'destinataire@example.com',
        }),
    )
    recipient_name = forms.CharField(
        label="Nom du destinataire",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom (optionnel)',
        }),
    )
    message = forms.CharField(
        label="Message personnalisé",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Bonjour, je vous partage ce document...',
        }),
    )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = DocumentCategory
        fields = ['name', 'icon', 'color', 'description', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'bi-folder'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
