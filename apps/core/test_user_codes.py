import pytest

from apps.core.utils.user_codes import SYSTEM_OPERATOR_CODE, format_user_public_code


@pytest.mark.django_db
def test_format_user_public_code_uses_stable_public_id(admin_user):
    assert format_user_public_code(admin_user) == f"USR-{admin_user.pk:06d}"


def test_format_user_public_code_uses_system_code_without_user():
    assert format_user_public_code(None) == SYSTEM_OPERATOR_CODE