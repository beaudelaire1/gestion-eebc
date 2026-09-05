"""Formulaires pour le module Jeunesse."""

from django import forms
from apps.core.forms import EnhancedModelForm
from .models import YoungMember, YouthGroup, YouthEvent, YouthAttendance


class YoungMemberForm(EnhancedModelForm):
    """Formulaire de création / édition d'un jeune."""

    class Meta:
        model = YoungMember
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 'photo',
            'site', 'group', 'family', 'linked_member',
            'phone', 'email', 'address', 'city', 'postal_code',
            'parent_name', 'parent_phone', 'parent_email',
            'emergency_contact', 'emergency_phone',
            'allergies', 'medical_notes',
            'is_baptized', 'baptism_date', 'is_born_again', 'conversion_date',
            'needs_transport', 'pickup_address', 'assigned_driver',
            'status', 'notes',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'baptism_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'conversion_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'pickup_address': forms.Textarea(attrs={'rows': 2}),
            'allergies': forms.Textarea(attrs={'rows': 2}),
            'medical_notes': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Conducteurs disponibles
        try:
            from apps.transport.models import DriverProfile
            self.fields['assigned_driver'].queryset = DriverProfile.objects.filter(
                is_available=True
            ).select_related('user')
        except Exception:
            pass

        # « Groupe » désigne ici une tranche d'âge de la jeunesse, distincte des
        # groupes d'église de la rubrique Gestion. Un menu vide n'expliquait pas
        # laquelle des deux listes il fallait alimenter.
        group_field = self.fields['group']
        group_field.queryset = YouthGroup.objects.filter(is_active=True)
        group_field.empty_label = "— Aucun groupe —"
        if not group_field.queryset.exists():
            group_field.help_text = (
                "Aucun groupe de jeunesse n'est encore créé. Les groupes de la "
                "rubrique Gestion sont des groupes d'église, distincts de ceux-ci : "
                "créez un groupe de jeunesse pour le proposer ici."
            )

    def clean(self):
        cleaned_data = super().clean()
        is_baptized = cleaned_data.get('is_baptized')
        baptism_date = cleaned_data.get('baptism_date')

        if is_baptized and not baptism_date:
            self.add_error('baptism_date', "La date de baptême est requise si le jeune est baptisé.")

        needs_transport = cleaned_data.get('needs_transport')
        pickup_address = cleaned_data.get('pickup_address')

        if needs_transport and not pickup_address:
            self.add_error('pickup_address', "L'adresse de ramassage est requise si le transport est demandé.")

        return cleaned_data


class YouthGroupForm(EnhancedModelForm):
    """Formulaire de groupe de jeunesse."""

    class Meta:
        model = YouthGroup
        fields = ['name', 'min_age', 'max_age', 'description', 'color', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'color': forms.TextInput(attrs={'type': 'color'}),
        }


class YouthEventForm(EnhancedModelForm):
    """Formulaire d'activité jeunesse."""

    class Meta:
        model = YouthEvent
        fields = [
            'title', 'event_type', 'date', 'start_time', 'end_time',
            'location', 'description', 'site', 'is_cancelled',
        ]
        widgets = {
            'date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class YoungMemberSearchForm(forms.Form):
    """Formulaire de recherche / filtre des jeunes."""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Rechercher par nom, prénom...',
            'class': 'form-control',
        }),
    )
    group = forms.ModelChoiceField(
        queryset=YouthGroup.objects.filter(is_active=True),
        required=False,
        empty_label="Tous les groupes",
    )
    status = forms.ChoiceField(
        choices=[('', 'Tous les statuts')] + list(YoungMember.Status.choices),
        required=False,
    )
    baptized = forms.ChoiceField(
        choices=[('', 'Tous'), ('yes', 'Baptisés'), ('no', 'Non baptisés')],
        required=False,
    )
    transport = forms.ChoiceField(
        choices=[('', 'Tous'), ('yes', 'Avec transport'), ('no', 'Sans transport')],
        required=False,
    )
