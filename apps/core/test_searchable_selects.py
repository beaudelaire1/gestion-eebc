"""Menus déroulants adossés à des listes longues."""
import pytest

from apps.bibleclub.forms import ChildForm
from apps.core.forms import make_field_searchable
from apps.members.forms import MemberForm
from apps.young.forms import YoungMemberForm


pytestmark = pytest.mark.django_db


def _classes(form, name):
    return set(form.fields[name].widget.attrs.get('class', '').split())


def test_helper_keeps_the_classes_already_set():
    from django import forms

    field = forms.ModelChoiceField(queryset=None)
    field.widget.attrs['class'] = 'custom'

    make_field_searchable(field, 'Chercher…')

    assert _classes_of(field) == {'custom', 'form-select', 'tom-select'}
    assert field.widget.attrs['data-placeholder'] == 'Chercher…'


def _classes_of(field):
    return set(field.widget.attrs.get('class', '').split())


def test_helper_tolerates_a_missing_field():
    assert make_field_searchable(None) is None


@pytest.mark.parametrize('field_name', ['linked_member', 'family', 'assigned_driver'])
def test_youth_form_long_menus_are_searchable(field_name):
    """Associer un jeune à une fiche membre suppose de chercher dans l'annuaire."""
    assert 'tom-select' in _classes(YoungMemberForm(), field_name)


def test_member_form_family_menu_is_searchable():
    assert 'tom-select' in _classes(MemberForm(), 'family')


def test_child_form_driver_menu_is_searchable():
    assert 'tom-select' in _classes(ChildForm(), 'assigned_driver')


def test_youth_member_menu_lists_active_members_and_the_current_link():
    """Rouvrir la fiche ne doit pas effacer un lien vers un membre inactif."""
    from apps.members.models import Member
    from apps.young.models import YoungMember
    from datetime import date

    actif = Member.objects.create(first_name='Ana', last_name='Active')
    inactif = Member.objects.create(
        first_name='Ivo', last_name='Inactif', status=Member.Status.INACTIF
    )
    young = YoungMember.objects.create(
        first_name='Sheskah',
        last_name='Cadet',
        date_of_birth=date(2010, 1, 1),
        gender=YoungMember.Gender.FEMININ,
        linked_member=inactif,
    )

    choices = set(YoungMemberForm(instance=young).fields['linked_member'].queryset)
    fresh = set(YoungMemberForm().fields['linked_member'].queryset)

    assert choices == {actif, inactif}
    assert fresh == {actif}
