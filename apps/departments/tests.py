"""
Tests pour l'app departments — modèle Department.
"""
import pytest

from apps.accounts.models import User
from apps.departments.models import Department


@pytest.fixture
def site(db):
    from apps.core.models import Site
    return Site.objects.first() or Site.objects.create(name='Cayenne', code='CAY')


@pytest.fixture
def leader(db):
    return User.objects.create_user(
        username='leader', email='leader@example.com', password='Pass123!'
    )


@pytest.mark.django_db
class TestDepartment:

    def test_create_department(self, site, leader):
        dept = Department.objects.create(
            name='Louange',
            description='Département musique et louange',
            site=site,
            leader=leader,
            is_active=True,
        )
        assert dept.pk is not None
        assert str(dept) == 'Louange'

    def test_member_count_empty(self, site, leader):
        dept = Department.objects.create(name='Vide', site=site, leader=leader)
        assert dept.member_count == 0
