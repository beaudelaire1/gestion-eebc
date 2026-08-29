"""Regression tests for EEBC multichannel announcement delivery."""

import pytest
from django.core import mail

from apps.accounts.models import User
from apps.members.models import Member

from .models import Announcement, EmailLog, SMSLog, UnsubscribePreference
from .multichannel import (
    get_announcement_email_recipients,
    get_announcement_whatsapp_recipients,
)

pytestmark = [pytest.mark.django_db, pytest.mark.security]


def make_member(
    name,
    *,
    role="membre",
    email=True,
    whatsapp=True,
    notify_email=True,
    notify_whatsapp=True,
):
    user = User.objects.create_user(
        username=f"user-{name}",
        email=f"{name}@example.test",
        password="SecurePass!2026",
        role=role,
    )
    return Member.objects.create(
        user=user,
        first_name=name.capitalize(),
        last_name="Test",
        email=f"{name}@example.test" if email else "",
        whatsapp_number="0694123456" if whatsapp else "",
        notify_by_email=notify_email,
        notify_by_whatsapp=notify_whatsapp,
        status=Member.Status.ACTIF,
    )


def make_announcement(**kwargs):
    defaults = {
        "title": "Information importante",
        "content": "Message de test pour les membres EEBC.",
        "visibility": Announcement.Visibility.MEMBERS,
        "notify_by_email": False,
        "notify_by_sms": False,
    }
    defaults.update(kwargs)
    return Announcement.objects.create(**defaults)


def test_channel_recipient_selection_respects_member_preferences():
    both = make_member("both")
    email_only = make_member("emailonly", notify_whatsapp=False)
    whatsapp_only = make_member("whatsonly", notify_email=False)
    make_member("none", notify_email=False, notify_whatsapp=False)
    announcement = make_announcement()

    email_recipients = {
        item["email"] for item in get_announcement_email_recipients(announcement)
    }
    whatsapp_recipients = {
        item["name"] for item in get_announcement_whatsapp_recipients(announcement)
    }

    assert both.email in email_recipients
    assert email_only.email in email_recipients
    assert whatsapp_only.email not in email_recipients
    assert both.full_name in whatsapp_recipients
    assert whatsapp_only.full_name in whatsapp_recipients
    assert email_only.full_name not in whatsapp_recipients


def test_staff_announcement_does_not_leak_to_ordinary_members():
    staff = make_member("staff", role="secretariat")
    ordinary = make_member("ordinary")
    announcement = make_announcement(visibility=Announcement.Visibility.STAFF)

    email_names = {
        item["name"] for item in get_announcement_email_recipients(announcement)
    }
    whatsapp_names = {
        item["name"] for item in get_announcement_whatsapp_recipients(announcement)
    }

    assert staff.full_name in email_names
    assert staff.full_name in whatsapp_names
    assert ordinary.full_name not in email_names
    assert ordinary.full_name not in whatsapp_names


def test_email_unsubscribe_is_enforced():
    member = make_member("unsubscribed")
    UnsubscribePreference.objects.create(
        email=member.email,
        notification_type=UnsubscribePreference.NotificationType.ALL,
        unsubscribe_token="11111111-1111-1111-1111-111111111111",
    )
    announcement = make_announcement()

    recipients = get_announcement_email_recipients(announcement)
    assert member.email not in {item["email"] for item in recipients}


def test_requested_announcement_attempts_email_and_whatsapp(
    django_capture_on_commit_callbacks,
):
    member = make_member("dual")

    with django_capture_on_commit_callbacks(execute=True):
        announcement = make_announcement(notify_by_email=True, notify_by_sms=True)

    assert EmailLog.objects.filter(
        recipient_email=member.email,
        status=EmailLog.Status.SENT,
    ).exists()
    assert len(mail.outbox) == 1

    # Test settings do not contain Meta credentials. A WhatsApp log in FAILED
    # state proves the second channel was attempted without making a network call.
    assert SMSLog.objects.filter(
        recipient_name=member.full_name,
        status=SMSLog.Status.FAILED,
    ).exists()

    announcement.refresh_from_db()
    assert announcement.notify_by_email is True
    assert announcement.notify_by_sms is True
