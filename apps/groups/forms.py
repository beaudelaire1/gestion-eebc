from django import forms
from django.contrib.auth import get_user_model
from .models import Group, GroupMeeting
from apps.members.models import Member

User = get_user_model()


class GroupForm(forms.ModelForm):
    """Formulaire pour créer/modifier un groupe."""
    
    class Meta:
        model = Group
        fields = [
            'name', 'description', 'group_type', 'leader', 
            'meeting_day', 'meeting_time', 'meeting_location', 
            'meeting_frequency', 'color', 'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du groupe'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description du groupe'
            }),
            'group_type': forms.Select(attrs={'class': 'form-select'}),
            'leader': forms.Select(attrs={'class': 'form-select'}),
            'meeting_day': forms.Select(attrs={'class': 'form-select'}),
            'meeting_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'meeting_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lieu de réunion'
            }),
            'meeting_frequency': forms.Select(attrs={'class': 'form-select'}),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'image': forms.FileInput(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les utilisateurs pour ne montrer que ceux avec des rôles appropriés
        self.fields['leader'].queryset = User.objects.filter(
            role__in=['admin', 'responsable_groupe', 'secretariat']
        ).order_by('first_name', 'last_name')
        self.fields['leader'].empty_label = "Sélectionner un responsable"


class GroupMembersForm(forms.Form):
    """Formulaire pour gérer les membres d'un groupe."""
    
    members = forms.ModelMultipleChoiceField(
        queryset=Member.objects.filter(status='actif'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Membres"
    )
    
    def __init__(self, *args, **kwargs):
        group = kwargs.pop('group', None)
        super().__init__(*args, **kwargs)
        
        if group:
            self.fields['members'].initial = group.members.all()
        
        # Ordonner les membres par nom
        self.fields['members'].queryset = Member.objects.filter(
            status='actif'
        ).order_by('last_name', 'first_name')


class GroupMeetingForm(forms.ModelForm):
    """Formulaire pour planifier une réunion de groupe."""
    
    class Meta:
        model = GroupMeeting
        fields = ['date', 'time', 'location', 'topic', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lieu de la réunion'
            }),
            'topic': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sujet de la réunion'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes sur la réunion'
            })
        }
    
    def __init__(self, *args, **kwargs):
        group = kwargs.pop('group', None)
        super().__init__(*args, **kwargs)
        
        # Pré-remplir avec les informations du groupe si disponibles
        if group and not self.instance.pk:
            if group.meeting_time:
                self.fields['time'].initial = group.meeting_time
            if group.meeting_location:
                self.fields['location'].initial = group.meeting_location


class GroupMeetingAttendanceForm(forms.ModelForm):
    """Formulaire pour enregistrer la présence à une réunion."""
    
    class Meta:
        model = GroupMeeting
        fields = ['attendees_count', 'notes']
        widgets = {
            'attendees_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Nombre de participants'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes sur la réunion'
            })
        }