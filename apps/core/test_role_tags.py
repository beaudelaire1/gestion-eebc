"""Le filtre de rôle doit comprendre le champ CSV, contrairement à `==`."""

import pytest
from django.template import Context, Template

from apps.accounts.models import User
from apps.core.templatetags.role_tags import has_any_role, has_management_role

pytestmark = pytest.mark.django_db


def _user(role, **kwargs):
    return User.objects.create_user(
        username=f'role-{role or "vide"}-{kwargs.get("suffix", "")}'.strip('-'),
        email='r@example.test',
        password='SecurePass!2026',
        role=role,
        is_superuser=kwargs.get('is_superuser', False),
    )


def test_single_role_matches():
    assert has_any_role(_user('admin'), 'admin,secretariat') is True


def test_multi_role_account_is_recognised():
    """Le cas qui cassait : `user.role == 'admin'` est faux pour 'admin,finance'."""
    user = _user('admin,finance')

    assert user.role != 'admin'          # l'ancienne condition échouait
    assert has_any_role(user, 'admin,secretariat') is True


def test_role_not_held_is_refused():
    assert has_any_role(_user('membre'), 'admin,secretariat') is False


def test_superuser_passes_every_role_check():
    assert has_any_role(_user('membre', is_superuser=True, suffix='su'), 'finance') is True


def test_anonymous_is_refused():
    from django.contrib.auth.models import AnonymousUser
    assert has_any_role(AnonymousUser(), 'admin') is False


def test_management_role_distinguishes_member_and_privileged_account():
    assert has_management_role(_user('membre', suffix='member')) is False
    assert has_management_role(_user('finance', suffix='finance')) is True


def test_empty_role_list_is_refused():
    assert has_any_role(_user('admin', suffix='empty'), '') is False


def test_filter_renders_in_a_template():
    user = _user('secretariat,responsable_groupe', suffix='tpl')
    tpl = Template(
        '{% load role_tags %}'
        '{% if user|has_any_role:"admin,secretariat" %}visible{% else %}masque{% endif %}'
    )

    assert tpl.render(Context({'user': user})) == 'visible'
