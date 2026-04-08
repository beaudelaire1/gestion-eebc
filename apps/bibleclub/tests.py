"""
Tests pour l'app bibleclub — modèles, validations.
"""
import pytest
from datetime import date, timedelta
from django.core.exceptions import ValidationError

from apps.bibleclub.models import AgeGroup, BibleClass, Child, Session, Attendance


# =============================================================================
# MODELS
# =============================================================================

@pytest.mark.django_db
class TestAgeGroup:

    def test_create_age_group(self):
        ag = AgeGroup.objects.create(name='Petits', min_age=3, max_age=6)
        assert ag.pk is not None
        assert 'Petits' in str(ag)

    def test_clean_min_greater_than_max(self):
        ag = AgeGroup(name='Invalid', min_age=10, max_age=5)
        with pytest.raises(ValidationError):
            ag.clean()


@pytest.mark.django_db
class TestBibleClass:

    def test_create_class(self):
        ag = AgeGroup.objects.create(name='Moyens', min_age=7, max_age=10)
        bc = BibleClass.objects.create(age_group=ag, room='Salle A', max_capacity=20)
        assert bc.pk is not None
        assert str(bc)

    def test_children_count_empty(self):
        ag = AgeGroup.objects.create(name='Grands', min_age=11, max_age=14)
        bc = BibleClass.objects.create(age_group=ag, room='Salle B')
        assert bc.children_count == 0


@pytest.mark.django_db
class TestChild:

    def test_create_child(self):
        ag = AgeGroup.objects.create(name='Petits', min_age=3, max_age=6)
        bc = BibleClass.objects.create(age_group=ag, room='Salle C')
        child = Child.objects.create(
            first_name='Léa',
            last_name='Martin',
            date_of_birth=date.today() - timedelta(days=365 * 5),
            bible_class=bc,
            father_name='Pierre Martin',
            father_phone='0694111222',
        )
        assert child.pk is not None
        assert child.full_name == 'Léa Martin'
        assert child.age >= 4

    def test_child_str(self):
        ag = AgeGroup.objects.create(name='Test', min_age=3, max_age=6)
        bc = BibleClass.objects.create(age_group=ag, room='R1')
        child = Child.objects.create(
            first_name='Lucas',
            last_name='Dupont',
            date_of_birth=date.today() - timedelta(days=365 * 4),
            bible_class=bc,
        )
        assert 'Lucas' in str(child)


@pytest.mark.django_db
class TestSession:

    def test_create_session(self):
        session = Session.objects.create(
            date=date.today(),
            theme='La création',
        )
        assert session.pk is not None
        assert str(session)

    def test_session_date_unique(self):
        Session.objects.create(date=date.today(), theme='Theme 1')
        with pytest.raises(Exception):
            Session.objects.create(date=date.today(), theme='Theme 2')


@pytest.mark.django_db
class TestAttendance:

    def test_record_attendance(self):
        ag = AgeGroup.objects.create(name='Att', min_age=3, max_age=6)
        bc = BibleClass.objects.create(age_group=ag, room='R2')
        child = Child.objects.create(
            first_name='Emma', last_name='Test',
            date_of_birth=date.today() - timedelta(days=365 * 5),
            bible_class=bc,
        )
        session = Session.objects.create(date=date.today(), theme='Test')
        att = Attendance.objects.create(
            session=session,
            child=child,
            bible_class=bc,
            status='present',
        )
        assert att.pk is not None
