"""Multichannel announcement delivery for EEBC.

One business notification can be delivered through email and WhatsApp while
respecting each member's communication preferences. The orchestration is kept
outside HTTP views so the same behavior can be reused by Celery and future
notification sources.
"""
from __future__ import annotations

import html
import logging
import os
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from apps.members.models import Member

from .models import Announcement, SMSLog, UnsubscribePreference
from .services import EmailService, WhatsAppMetaService

logger = logging.getLogger(__name__)


def _is_staff_member(member: Member) -> bool:
    user = getattr(member, "user", None)
    if not user:
        return False
    return user.has_any_role(
        "admin",
        "secretariat",
        "pasteur",
        "ancien",
        "diacre",
        "responsable_club",
        "moniteur",
        "finance",
    )


def _eligible_members(announcement: Announcement):
    queryset = Member.objects.filter(status=Member.Status.ACTIF).select_related("user")
    if announcement.visibility == Announcement.Visibility.STAFF:
        return [member for member in queryset if _is_staff_member(member)]
    return list(queryset)


def _email_unsubscribed(email: str) -> bool:
    if not email:
        return True
    return UnsubscribePreference.objects.filter(
        email__iexact=email,
        notification_type__in=[
            UnsubscribePreference.NotificationType.ALL,
            UnsubscribePreference.NotificationType.ADMINISTRATIVE,
        ],
    ).exists()


def get_announcement_email_recipients(
    announcement: Announcement,
) -> List[Dict[str, str]]:
    recipients: List[Dict[str, str]] = []
    seen = set()
    for member in _eligible_members(announcement):
        email = (member.email or "").strip()
        normalized = email.lower()
        if not member.notify_by_email or not email or normalized in seen:
            continue
        if _email_unsubscribed(email):
            continue
        seen.add(normalized)
        recipients.append({"name": member.full_name, "email": email})
    return recipients


def get_announcement_whatsapp_recipients(
    announcement: Announcement,
) -> List[Dict[str, str]]:
    recipients: List[Dict[str, str]] = []
    seen = set()
    for member in _eligible_members(announcement):
        phone = (member.whatsapp_number or "").strip()
        normalized = WhatsAppMetaService._normalize_phone(phone)
        if not member.notify_by_whatsapp or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        recipients.append({"name": member.full_name, "phone": phone})
    return recipients


def _priority_label(announcement: Announcement) -> str:
    return {
        Announcement.Priority.LOW: "Information",
        Announcement.Priority.NORMAL: "Annonce",
        Announcement.Priority.HIGH: "Important",
        Announcement.Priority.URGENT: "Urgent",
    }.get(announcement.priority, "Annonce")


def _plain_content(announcement: Announcement) -> str:
    """Convert rich editor markup to readable WhatsApp text."""
    raw = BeautifulSoup(announcement.content or "", "html.parser").get_text(" ")
    return " ".join(html.unescape(raw).split())


def send_announcement_email(announcement: Announcement) -> Dict[str, int]:
    recipients = get_announcement_email_recipients(announcement)
    sent = 0
    failed = 0
    subject = f"{_priority_label(announcement)} EEBC — {announcement.title}"

    for recipient in recipients:
        log = EmailService.send_email(
            recipient_email=recipient["email"],
            recipient_name=recipient["name"],
            subject=subject,
            template_name="emails/announcement_notification.html",
            context={
                "announcement": announcement,
                "recipient_name": recipient["name"],
                "priority_label": _priority_label(announcement),
            },
            fail_silently=True,
        )
        if log.status == "sent":
            sent += 1
        else:
            failed += 1

    return {"total": len(recipients), "sent": sent, "failed": failed}


def _whatsapp_template_name() -> str:
    return os.environ.get("META_WHATSAPP_ANNOUNCEMENT_TEMPLATE", "").strip()


def _whatsapp_template_language() -> str:
    return os.environ.get("META_WHATSAPP_TEMPLATE_LANGUAGE", "fr").strip() or "fr"


def _send_whatsapp_template(
    recipient: Dict[str, str], announcement: Announcement
) -> bool:
    normalized_phone = WhatsAppMetaService._normalize_phone(recipient["phone"])
    plain_content = _plain_content(announcement)
    message_summary = (
        f"{_priority_label(announcement)}: {announcement.title} — {plain_content}"
    )
    log = SMSLog.objects.create(
        recipient_phone=normalized_phone,
        recipient_name=recipient["name"],
        message=message_summary,
        status=SMSLog.Status.PENDING,
    )

    if not WhatsAppMetaService._is_configured():
        log.status = SMSLog.Status.FAILED
        log.error_message = "Meta WhatsApp non configuré."
        log.save(update_fields=["status", "error_message"])
        return False

    payload = {
        "messaging_product": "whatsapp",
        "to": normalized_phone,
        "type": "template",
        "template": {
            "name": _whatsapp_template_name(),
            "language": {"code": _whatsapp_template_language()},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": recipient["name"] or "Membre EEBC",
                        },
                        {"type": "text", "text": announcement.title},
                        {"type": "text", "text": plain_content},
                    ],
                }
            ],
        },
    }

    try:
        response = requests.post(
            WhatsAppMetaService._build_endpoint(),
            headers=WhatsAppMetaService._build_headers(),
            json=payload,
            timeout=20,
        )
        if response.ok:
            data = response.json()
            messages = data.get("messages") or []
            log.external_id = messages[0].get("id", "") if messages else ""
            log.status = SMSLog.Status.SENT
            log.sent_at = timezone.now()
            log.save(update_fields=["external_id", "status", "sent_at"])
            return True

        error_message = f"HTTP {response.status_code}"
        try:
            error_message = response.json().get("error", {}).get(
                "message", error_message
            )
        except (TypeError, ValueError):
            pass
        log.status = SMSLog.Status.FAILED
        log.error_message = error_message
        log.save(update_fields=["status", "error_message"])
        return False
    except requests.RequestException as exc:
        log.status = SMSLog.Status.FAILED
        log.error_message = str(exc)
        log.save(update_fields=["status", "error_message"])
        return False


def send_announcement_whatsapp(announcement: Announcement) -> Dict[str, int]:
    recipients = get_announcement_whatsapp_recipients(announcement)
    sent = 0
    failed = 0
    template_name = _whatsapp_template_name()
    plain_content = _plain_content(announcement)

    for recipient in recipients:
        if template_name:
            success = _send_whatsapp_template(recipient, announcement)
        else:
            # Compatibility fallback for installations that still use the
            # 24-hour customer-service window. Proactive production messages
            # should configure META_WHATSAPP_ANNOUNCEMENT_TEMPLATE.
            result = WhatsAppMetaService.send_text_message(
                recipient_phone=recipient["phone"],
                recipient_name=recipient["name"],
                message=(
                    f"[{_priority_label(announcement)}] {announcement.title}\n\n"
                    f"{plain_content}\n\nEEBC"
                ),
            )
            success = bool(result.get("success"))

        if success:
            sent += 1
        else:
            failed += 1

    return {"total": len(recipients), "sent": sent, "failed": failed}
