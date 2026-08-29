"""Regression tests for announcement templates and channel presentation."""

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.members.models import Member

from .models import Announcement
from .multichannel import _plain_content

pytestmark = [pytest.mark.django_db]


def make_admin():
    return User.objects.create_user(
        username="announcement-admin",
        email="announcement-admin@example.test",
        password="SecurePass!2026",
        role="admin",
    )


def test_create_template_exposes_complete_multichannel_form(client):
    client.force_login(make_admin())

    response = client.get(reverse("communication:announcement_create"))

    assert response.status_code == 200
    assert b'name="priority"' in response.content
    assert b'name="visibility"' in response.content
    assert b'name="start_date"' in response.content
    assert b'name="end_date"' in response.content
    assert b'name="notify_by_email"' in response.content
    assert "Notifier les destinataires par email + WhatsApp" in response.content.decode()
    assert "Respect des préférences membres" in response.content.decode()


def test_detail_template_exposes_requested_delivery_channels(client):
    admin = make_admin()
    announcement = Announcement.objects.create(
        title="Annonce multicanal",
        content="<p>Message <strong>important</strong></p>",
        created_by=admin,
        notify_by_email=True,
    )
    client.force_login(admin)

    response = client.get(
        reverse("communication:announcement_detail", kwargs={"pk": announcement.pk})
    )

    body = response.content.decode()
    assert response.status_code == 200
    assert "Email" in body
    assert "WhatsApp" in body
    assert "<strong>important</strong>" in body


def test_whatsapp_content_is_plain_text():
    announcement = Announcement(
        title="HTML",
        content="<p>Bonjour <strong>EEBC</strong><br>Rendez-vous &amp; informations</p>",
    )

    assert _plain_content(announcement) == "Bonjour EEBC Rendez-vous & informations"


def test_member_preferences_keep_email_and_whatsapp_independent(client):
    admin = make_admin()
    member = Member.objects.create(
        first_name="Marie",
        last_name="Canaux",
        notify_by_email=True,
        notify_by_whatsapp=False,
        whatsapp_number="0694123456",
    )

    assert member.notify_by_email is True
    assert member.notify_by_whatsapp is False
