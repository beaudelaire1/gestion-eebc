"""
Tests pour l'app inventory — modèles Equipment, Category.
"""
import pytest
from decimal import Decimal
from datetime import date

from apps.accounts.models import User
from apps.inventory.models import Category, Equipment


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='invuser', email='inv@example.com', password='Pass123!'
    )


@pytest.mark.django_db
class TestCategory:

    def test_create_category(self):
        cat = Category.objects.create(name='Sono', description='Matériel de sonorisation')
        assert cat.pk is not None
        assert str(cat) == 'Sono'


@pytest.mark.django_db
class TestEquipment:

    def test_create_equipment(self, user):
        cat = Category.objects.create(name='Mobilier')
        eq = Equipment.objects.create(
            name='Chaise pliante',
            category=cat,
            quantity=50,
            condition='good',
            location='Réserve',
            responsible=user,
        )
        assert eq.pk is not None
        assert 'Chaise pliante' in str(eq)

    def test_needs_attention_broken(self, user):
        cat = Category.objects.create(name='Audio')
        eq = Equipment.objects.create(
            name='Micro cassé',
            category=cat,
            quantity=1,
            condition='broken',
            responsible=user,
        )
        assert eq.needs_attention is True

    def test_soft_delete(self, user):
        cat = Category.objects.create(name='Divers')
        eq = Equipment.objects.create(
            name='Tableau',
            category=cat,
            quantity=1,
            responsible=user,
            is_active=True,
        )
        eq.soft_delete()
        eq.refresh_from_db()
        assert eq.is_active is False

    def test_restore(self, user):
        cat = Category.objects.create(name='Divers2')
        eq = Equipment.objects.create(
            name='Projecteur',
            category=cat,
            quantity=1,
            responsible=user,
            is_active=False,
        )
        eq.restore()
        eq.refresh_from_db()
        assert eq.is_active is True
