"""
apps/communication/forms.py - Formulaires pour la communication.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Notification, Announcement, EmailLog, SMSLog


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
