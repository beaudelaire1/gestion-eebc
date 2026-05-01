from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone


def _create_document(*, title, admin_user, is_confidential=False):
    from apps.documents.models import Document

    content = b"Document de test"
    upload = SimpleUploadedFile(f"{title}.txt", content, content_type="text/plain")
    return Document.objects.create(
        title=title,
        file=upload,
        file_name=f"{title}.txt",
        file_size=len(content),
        file_type="text/plain",
        media_type=Document.MediaType.DOCUMENT,
        is_confidential=is_confidential,
        uploaded_by=admin_user,
        visibility=Document.Visibility.STAFF,
    )


@pytest.mark.django_db
def test_document_stats_page_does_not_render_recent_queryset(authenticated_client, admin_user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    recent_document = _create_document(title="recent", admin_user=admin_user, is_confidential=True)
    old_document = _create_document(title="ancien", admin_user=admin_user)
    old_date = timezone.now() - timedelta(days=45)
    type(old_document).objects.filter(pk=old_document.pk).update(created_at=old_date)

    response = authenticated_client.get(reverse("documents:stats"))

    assert response.status_code == 200
    assert b"QuerySet" not in response.content
    assert b"Derniers 30 jours" in response.content
    assert b"Confidentiels" in response.content
    assert recent_document.is_confidential is True


@pytest.mark.django_db
def test_documents_stats_recent_count_and_confidential_for_admin(admin_user, settings, tmp_path):
    from apps.documents.services import get_documents_stats

    settings.MEDIA_ROOT = tmp_path
    _create_document(title="recent", admin_user=admin_user, is_confidential=True)
    old_document = _create_document(title="ancien", admin_user=admin_user)
    old_date = timezone.now() - timedelta(days=45)
    type(old_document).objects.filter(pk=old_document.pk).update(created_at=old_date)

    stats = get_documents_stats(admin_user)

    assert stats["total"] == 2
    assert stats["confidential"] == 1
    assert stats["recent_count"] == 1
