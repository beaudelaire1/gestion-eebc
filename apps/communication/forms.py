"""
apps/communication/forms.py - Formulaires pour la communication.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from apps.core.widgets import TinyMCEWidget
from .models import Notification, Announcement, EmailLog, EmailSenderDepartment, SMSLog


class NotificationForm(forms.ModelForm):
    """Formulaire pour créer/modifier une notification."""
    
    class Meta:
        model = Notification
        fields = [
            'user', 'title', 'message', 'notification_type', 'action_url'
        ]
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-select',
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de la notification',
                'maxlength': '200'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Message'
            }),
            'notification_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'action_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lien optionnel (https://...)'
            }),
        }
        labels = {
            'user': 'Destinataire',
            'title': 'Titre',
            'message': 'Message',
            'notification_type': 'Type',
            'action_url': 'Lien d\'action',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        title = cleaned_data.get('title', '').strip()
        message = cleaned_data.get('message', '').strip()
        
        if not title:
            raise ValidationError("Le titre est requis.")
        
        if not message or len(message) < 10:
            raise ValidationError("Le message doit contenir au moins 10 caractères.")
        
        return cleaned_data


class AnnouncementForm(forms.ModelForm):
    """Formulaire pour les annonces."""
    
    class Meta:
        model = Announcement
        fields = [
            'title', 'content', 'priority', 'visibility',
            'start_date', 'end_date', 'is_pinned',
            'notify_by_email', 'notify_by_sms'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de l\'annonce',
                'required': True,
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Contenu de l\'annonce',
                'required': True,
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'visibility': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'is_pinned': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notify_by_email': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notify_by_sms': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_date'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']
        self.fields['end_date'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']
        self.fields['end_date'].required = False
    
    def clean_end_date(self):
        end_date = self.cleaned_data.get('end_date')
        start_date = self.cleaned_data.get('start_date')
        
        if end_date and start_date and end_date <= start_date:
            raise ValidationError("La date de fin doit être après la date de début.")
        
        return end_date
    
    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if len(title) < 3:
            raise ValidationError("Le titre doit contenir au moins 3 caractères.")
        return title


class BulkNotificationForm(forms.Form):
    """Formulaire pour envoyer des notifications en masse."""
    
    RECIPIENT_CHOICES = [
        ('all', 'Tous les utilisateurs'),
        ('active_members', 'Membres actifs'),
        ('pastors', 'Pasteurs'),
        ('secretariat', 'Secrétariat'),
        ('custom', 'Sélection personnalisée'),
    ]
    
    recipient_type = forms.ChoiceField(
        choices=RECIPIENT_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Titre'
        })
    )
    
    message = forms.CharField(
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Message'
        })
    )
    
    notification_type = forms.ChoiceField(
        choices=Notification.Type.choices,
        initial='info',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    recipients = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import User
        self.fields['recipients'].queryset = User.objects.filter(is_active=True)


class EmailLogFilterForm(forms.Form):
    """Formulaire de filtrage des logs email."""
    
    status = forms.ChoiceField(
        choices=[('', 'Tous les statuts')] + list(EmailLog.Status.choices),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        required=False
    )
    
    recipient = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email du destinataire'
        }),
        required=False
    )
    
    from_date = forms.DateField(
        widget=forms.DateInput(format='%Y-%m-%d', attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )
    
    to_date = forms.DateField(
        widget=forms.DateInput(format='%Y-%m-%d', attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )


class MultipleFileInput(forms.ClearableFileInput):
    """Widget fichier acceptant la sélection multiple."""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Champ fichier multiple (pattern officiel Django 4.2+)."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)
    
    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]
        return [single_clean(data, initial)] if data else []


class ComposeEmailForm(forms.Form):
    """Formulaire de composition d'e-mail avec département expéditeur."""
    
    ATTACHMENT_ALLOWED_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.odt', '.ods', '.txt', '.csv', '.png', '.jpg', '.jpeg', '.gif', '.zip',
    }
    ATTACHMENT_MAX_TOTAL_BYTES = 10 * 1024 * 1024  # 10 Mo au total
    
    department = forms.ModelChoiceField(
        queryset=EmailSenderDepartment.objects.filter(is_active=True),
        label="Département expéditeur",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    recipients = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        label="Destinataires (équipes)",
        help_text="Comptes d'équipe (responsables, diacres, pasteurs, secrétariat...).",
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '8'})
    )
    
    external_recipients = forms.CharField(
        required=False,
        label="Destinataires (À)",
        help_text="Adresses externes (mairie, partenaires...), séparées par des virgules ou des retours à la ligne.",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'mairie@ville-cayenne.fr, partenaire@example.org'
        })
    )
    
    cc = forms.CharField(
        required=False,
        label="CC (Copie)",
        help_text="Adresses en copie, visibles de tous les destinataires.",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'copie1@example.org, copie2@example.org'
        })
    )
    
    bcc = forms.CharField(
        required=False,
        label="CCI (Copie cachée)",
        help_text="Adresses en copie cachée, invisibles des autres destinataires.",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'archive@eglise-ebc.org'
        })
    )
    
    subject = forms.CharField(
        max_length=200,
        label="Sujet",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Sujet de l'e-mail"
        })
    )
    
    body = forms.CharField(
        label="Message",
        widget=TinyMCEWidget(config={
            'height': 380,
            'plugins': 'advlist autolink lists link table code',
            'toolbar': (
                'undo redo | blocks | bold italic underline forecolor | '
                'alignleft aligncenter alignright | bullist numlist | '
                'link table | removeformat code'
            ),
        })
    )
    
    attachments = MultipleFileField(
        required=False,
        label="Pièces jointes",
        help_text="PDF, Office, images, ZIP — 10 Mo maximum au total.",
        widget=MultipleFileInput(attrs={'class': 'form-control', 'multiple': True})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import User
        self.fields['recipients'].queryset = (
            User.objects.filter(is_active=True)
            .exclude(email='')
            .filter(Q(is_superuser=True) | Q(is_staff=True) | ~Q(role='membre'))
            .order_by('last_name', 'first_name')
        )
    
    def clean_subject(self):
        subject = self.cleaned_data.get('subject', '').strip()
        if len(subject) < 3:
            raise ValidationError("Le sujet doit contenir au moins 3 caractères.")
        return subject
    
    def clean_external_recipients(self):
        """Normalise et valide la liste d'adresses externes."""
        import re

        from django.core.validators import validate_email
        
        raw = self.cleaned_data.get('external_recipients', '')
        emails = [e.strip() for e in re.split(r'[,;\n]+', raw) if e.strip()]
        for email in emails:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError(f"Adresse invalide : {email}")
        return emails
    
    def _clean_email_list(self, field_name):
        """Valide une liste d'adresses CC ou CCI."""
        import re

        from django.core.validators import validate_email
        
        raw = self.cleaned_data.get(field_name, '')
        emails = [e.strip() for e in re.split(r'[,;\n]+', raw) if e.strip()]
        for email in emails:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError(f"Adresse invalide : {email}")
        return emails
    
    def clean_cc(self):
        return self._clean_email_list('cc')
    
    def clean_bcc(self):
        return self._clean_email_list('bcc')
    
    def clean_attachments(self):
        """Vérifie extensions et taille totale des pièces jointes."""
        import os
        
        files = self.cleaned_data.get('attachments') or []
        total = 0
        for f in files:
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in self.ATTACHMENT_ALLOWED_EXTENSIONS:
                raise ValidationError(f"Type de fichier non autorisé : {f.name}")
            total += f.size
        if total > self.ATTACHMENT_MAX_TOTAL_BYTES:
            raise ValidationError("Les pièces jointes dépassent 10 Mo au total.")
        return files
    
    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('recipients') and not cleaned_data.get('external_recipients'):
            raise ValidationError("Sélectionnez au moins un destinataire (équipe ou adresse externe).")
        return cleaned_data
    
    def clean_body(self):
        from django.utils.html import strip_tags
        body = self.cleaned_data.get('body', '')
        if len(strip_tags(body).strip()) < 10:
            raise ValidationError("Le message doit contenir au moins 10 caractères.")
        return body


class SMSLogFilterForm(forms.Form):
    """Formulaire de filtrage des logs SMS."""
    
    status = forms.ChoiceField(
        choices=[('', 'Tous les statuts')] + list(SMSLog.Status.choices),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        required=False
    )
    
    phone = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Numéro de téléphone'
        }),
        required=False
    )
    
    from_date = forms.DateField(
        widget=forms.DateInput(format='%Y-%m-%d', attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )
    
    to_date = forms.DateField(
        widget=forms.DateInput(format='%Y-%m-%d', attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )
