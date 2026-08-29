"""
Tests pour l'app events — modèles, vues.
"""
import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User
from apps.events.models import EventCategory, Event, EventRegistration


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username='evadmin', email='evadmin@example.com',
        password='Admin123!', role='admin', is_staff=True,
    )


@pytest.fixture
def site(db):
    from apps.core.models import Site
    return Site.objects.first() or Site.objects.create(name='Cayenne', code='CAY')


@pytest.fixture
def category(db):
    return EventCategory.objects.create(name='Culte', color='#3B82F6')


@pytest.fixture
def event(db, site, category, admin_user):
    return Event.objects.create(
        title='Culte dominical',
        description='Culte du dimanche',
        site=site,
        category=category,
        start_date=timezone.now().date() + timedelta(days=1),
        start_time=timezone.now().time(),
    )


# =============================================================================
# MODELS
# =============================================================================

@pytest.mark.django_db
class TestEventCategory:

    def test_create_category(self):
        cat = EventCategory.objects.create(name='Prière', color='#10B981')
        assert cat.pk is not None
        assert str(cat) == 'Prière'


@pytest.mark.django_db
class TestEvent:

    def test_create_event(self, event):
        assert event.pk is not None
        assert 'Culte dominical' in str(event)

    def test_is_upcoming(self, event):
        assert event.is_upcoming is True

    def test_event_cancelled(self, event):
        event.is_cancelled = True
        event.save()
        event.refresh_from_db()
        assert event.is_cancelled is True

    def test_event_color_from_category(self, event):
        assert event.color == '#3B82F6'


@pytest.mark.django_db
class TestEventRegistration:

    def test_register_user(self, event, admin_user):
        reg = EventRegistration.objects.create(
            event=event,
            user=admin_user,
        )
        assert reg.pk is not None
        assert reg.registered_at is not None

    def test_unique_registration(self, event, admin_user):
        EventRegistration.objects.create(event=event, user=admin_user)
        with pytest.raises(Exception):
            EventRegistration.objects.create(event=event, user=admin_user)
