"""Celery tasks for independent notification channels."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def send_announcement_email_task(announcement_id: int):
    from .models import Announcement
    from .multichannel import send_announcement_email

    announcement = Announcement.objects.get(pk=announcement_id)
    result = send_announcement_email(announcement)
    logger.info("Announcement %s email delivery: %s", announcement_id, result)
    return result


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def send_announcement_whatsapp_task(announcement_id: int):
    from .models import Announcement
    from .multichannel import send_announcement_whatsapp

    announcement = Announcement.objects.get(pk=announcement_id)
    result = send_announcement_whatsapp(announcement)
    logger.info("Announcement %s WhatsApp delivery: %s", announcement_id, result)
    return result
