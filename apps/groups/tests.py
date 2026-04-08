"""
Tests pour l'app groups — modèles groupes cellulaires.
"""
import pytest
from datetime import date, time

from apps.accounts.models import User
from apps.groups.models import Group, GroupMeeting


@pytest.fixture
def site(db):
    from apps.core.models import Site
    return Site.objects.first() or Site.objects.create(name='Cayenne', code='CAY')


@pytest.mark.django_db
class TestGroup:

    def test_create_group(self, site):
        group = Group.objects.create(
            name='Groupe Espérance',
            description='Groupe de prière du quartier',
            site=site,
            meeting_day='lundi',
            meeting_time=time(19, 0),
            is_active=True,
        )
        assert group.pk is not None
        assert str(group) == 'Groupe Espérance'

    def test_member_count_empty(self, site):
        group = Group.objects.create(name='Vide', site=site)
        assert group.member_count == 0


@pytest.mark.django_db
class TestGroupMeeting:

    def test_create_meeting(self, site):
        group = Group.objects.create(name='Groupe Test', site=site)
        meeting = GroupMeeting.objects.create(
            group=group,
            date=date.today(),
            time=time(19, 30),
            topic='La foi',
            attendees_count=8,
        )
        assert meeting.pk is not None
        assert str(meeting)

    def test_cancelled_meeting(self, site):
        group = Group.objects.create(name='Groupe Cancel', site=site)
        meeting = GroupMeeting.objects.create(
            group=group,
            date=date.today(),
            is_cancelled=True,
        )
        assert meeting.is_cancelled is True
