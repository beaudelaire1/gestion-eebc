from django import forms
from .models import Document, DocumentCategory, GeneratedDocument
from .richtext import sanitize_generated_document_html


ROLE_CHOICES = [
    ('admin', 'Administrateur'),
    ('secretariat', 'Secrétariat'),
    ('pasteur', 'Pasteur'),
    ('ancien', 'Ancien'),
    ('diacre', 'Diacre'),
    ('finance', 'Finance'),
    ('encadrant', 'Encadrant'),
    ('responsable_club', 'Responsable Club Biblique'),
    ('moniteur', 'Moniteur'),
    ('chauffeur', 'Chauffeur'),
    ('responsable_groupe', 'Responsable de Groupe'),
    ('membre', 'Membre'),
]


class DocumentUploadForm(forms.ModelForm):
    allowed_roles_list = forms.MultipleChoiceField(
        label="Rôles autorisés",
        choices=ROLE_CHOICES,
        required=False,
        help_text="Utilisé uniquement si la visibilité est « Rôles spécifiques ».",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Document
        fields = ['title', 'description', 'file', 'category', 'source', 'tags',
                  'visibility', 'is_confidential']
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
            'visibility': forms.Select(attrs={'class': 'form-select'}),
            'is_confidential': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('visibility') == Document.Visibility.ROLES and not cleaned.get('allowed_roles_list'):
            raise forms.ValidationError(
                "Sélectionnez au moins un rôle lorsque la visibilité est « Rôles spécifiques »."
            )
        return cleaned


class DocumentEditForm(forms.ModelForm):
    allowed_roles_list = forms.MultipleChoiceField(
        label="Rôles autorisés",
        choices=ROLE_CHOICES,
        required=False,
        help_text="Utilisé uniquement si la visibilité est « Rôles spécifiques ».",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Document
        fields = ['title', 'description', 'category', 'source', 'tags',
                  'visibility', 'is_confidential']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'tag1, tag2, tag3...'}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
            'is_confidential': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['allowed_roles_list'].initial = self.instance.allowed_roles_list

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('visibility') == Document.Visibility.ROLES and not cleaned.get('allowed_roles_list'):
            raise forms.ValidationError(
                "Sélectionnez au moins un rôle lorsque la visibilité est « Rôles spécifiques »."
            )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.allowed_roles = ','.join(self.cleaned_data.get('allowed_roles_list') or [])
        if commit:
            instance.save()
        return instance


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


class GeneratedDocumentForm(forms.ModelForm):
    allowed_roles_list = forms.MultipleChoiceField(
        label="Rôles autorisés",
        choices=ROLE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = GeneratedDocument
        fields = [
            'title', 'kind', 'reference', 'document_date',
            'recipient_name', 'recipient_address', 'subject',
            'body_html',
            'signature_name', 'signature_title',
            'visibility',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Titre du document"}),
            'kind': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Auto si vide (ex. EEBC/CR/2026/01)'}),
            'document_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du destinataire (optionnel)'}),
            'recipient_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Adresse complète (optionnel)'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Objet du document"}),
            'body_html': forms.HiddenInput(),  # alimenté par Quill
            'signature_name': forms.TextInput(attrs={'class': 'form-control'}),
            'signature_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex. Pasteur principal, Secrétaire général'}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['allowed_roles_list'].initial = self.instance.allowed_roles_list
        initial_body_html = self.data.get('body_html') if self.is_bound else (self.initial.get('body_html') or getattr(self.instance, 'body_html', ''))
        self.fields['body_html'].initial = sanitize_generated_document_html(initial_body_html)

    def clean_body_html(self):
        return sanitize_generated_document_html(self.cleaned_data.get('body_html') or '')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('visibility') == Document.Visibility.ROLES and not cleaned.get('allowed_roles_list'):
            raise forms.ValidationError("Sélectionnez au moins un rôle pour la visibilité « Rôles ».")
        if not (cleaned.get('body_html') or '').strip():
            raise forms.ValidationError("Le contenu du document ne peut pas être vide.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.allowed_roles = ','.join(self.cleaned_data.get('allowed_roles_list') or [])
        if commit:
            instance.save()
        return instance
