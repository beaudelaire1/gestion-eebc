"""Champ « Groupe » du formulaire jeune."""
import pytest

from apps.young.forms import YoungMemberForm
from apps.young.models import YouthGroup


pytestmark = pytest.mark.django_db


def test_group_menu_lists_the_active_youth_groups():
    active = YouthGroup.objects.create(name='Ados', min_age=13, max_age=17)
    YouthGroup.objects.create(name='Archivé', min_age=18, max_age=25, is_active=False)

    choices = YoungMemberForm().fields['group'].queryset

    assert list(choices) == [active]


def test_empty_group_menu_explains_which_list_to_fill():
    """Un menu vide ne disait pas que les groupes d'église sont une autre liste."""
    field = YoungMemberForm().fields['group']

    assert not field.queryset.exists()
    assert 'groupe de jeunesse' in field.help_text
