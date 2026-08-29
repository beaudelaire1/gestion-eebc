"""
Tests pour l'app communication — modèles, formulaires.
"""
import pytest
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User
from apps.communication.models import (
    EmailLog,
    UnsubscribePreference,
    Announcement,
    Notification,
    EmailTemplate,
    SMSLog,
)


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='commuser', email='comm@example.com', password='Pass123!'
    )


# =============================================================================
# MODELS
# =============================================================================

@pytest.mark.django_db
class TestEmailLog:

    def test_create_email_log(self):
        log = EmailLog.objects.create(
            recipient_email='dest@example.com',
            subject='Test Subject',
            body='Test Body',
        )
        assert log.pk is not None
        assert str(log)

    def test_default_status_pending(self):
        log = EmailLog.objects.create(
            recipient_email='dest@example.com',
            subject='Test',
        )
        assert log.status == EmailLog.Status.PENDING

    def test_unsubscribe_token_generated(self):
        log = EmailLog.objects.create(
            recipient_email='dest@example.com',
            subject='Test',
        )
        assert log.unsubscribe_token is not None


@pytest.mark.django_db
class TestAnnouncement:

    def test_create_announcement(self, user):
        ann = Announcement.objects.create(
            title='Annonce Test',
            content='Contenu de test',
            created_by=user,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=7),
        )
        assert ann.pk is not None
        assert 'Annonce Test' in str(ann)

    def test_is_current_active(self, user):
        ann = Announcement.objects.create(
            title='Active',
            content='...',
            created_by=user,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
            is_active=True,
        )
        assert ann.is_current is True

    def test_is_current_expired(self, user):
        ann = Announcement.objects.create(
            title='Expired',
            content='...',
            created_by=user,
            start_date=timezone.now() - timedelta(days=7),
            end_date=timezone.now() - timedelta(days=1),
            is_active=True,
        )
        assert ann.is_current is False


@pytest.mark.django_db
class TestNotification:

    def test_create_notification(self, user):
        notif = Notification.objects.create(
            user=user,
            title='Notification Test',
            message='Message de test',
        )
        assert notif.pk is not None
        assert notif.is_read is False

    def test_mark_as_read(self, user):
        notif = Notification.objects.create(
            user=user,
            title='Read Test',
            message='...',
        )
        notif.mark_as_read()
        assert notif.is_read is True
        assert notif.read_at is not None


@pytest.mark.django_db
class TestEmailTemplate:

    def test_create_template(self):
        tpl = EmailTemplate.objects.create(
            name='Welcome',
            template_type='welcome',
            subject='Bienvenue',
            html_content='<h1>Bienvenue</h1>',
            is_active=True,
        )
        assert tpl.pk is not None

    def test_default_uniqueness(self):
        """Un seul template par défaut par type."""
        EmailTemplate.objects.create(
            name='Welcome 1',
            template_type='welcome',
            subject='Bienvenue 1',
            html_content='<h1>V1</h1>',
            is_default=True,
        )
        tpl2 = EmailTemplate.objects.create(
            name='Welcome 2',
            template_type='welcome',
            subject='Bienvenue 2',
            html_content='<h1>V2</h1>',
            is_default=True,
        )
        tpl2.save()
        # Le save() override devrait garantir 1 seul default par type
        defaults = EmailTemplate.objects.filter(
            template_type='welcome', is_default=True
        ).count()
        assert defaults == 1


@pytest.mark.django_db
class TestSMSLog:

    def test_create_sms_log(self):
        log = SMSLog.objects.create(
            recipient_phone='+594694000000',
            message='Test SMS',
        )
        assert log.pk is not None
        assert str(log)
