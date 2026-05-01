import sys
import types

import pytest
from django.contrib.messages import get_messages
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.urls import reverse


def test_document_storage_uses_filesystem_without_cloudinary(settings, tmp_path):
    from apps.documents.storage import DocumentStorage

    settings.CLOUDINARY_URL = ''
    settings.MEDIA_ROOT = tmp_path

    storage = DocumentStorage()

    assert isinstance(storage.backend, FileSystemStorage)


def test_document_storage_uses_raw_cloudinary_when_configured(settings, monkeypatch):
    from apps.documents.storage import DocumentStorage

    class FakeRawMediaCloudinaryStorage:
        pass

    package = types.ModuleType('cloudinary_storage')
    storage_module = types.ModuleType('cloudinary_storage.storage')
    storage_module.RawMediaCloudinaryStorage = FakeRawMediaCloudinaryStorage
    monkeypatch.setitem(sys.modules, 'cloudinary_storage', package)
    monkeypatch.setitem(sys.modules, 'cloudinary_storage.storage', storage_module)
    settings.CLOUDINARY_URL = 'cloudinary://key:secret@example'

    storage = DocumentStorage()

    assert isinstance(storage.backend, FakeRawMediaCloudinaryStorage)


def test_document_storage_reads_cloudinary_file_from_signed_url(settings, monkeypatch):
    from apps.documents.storage import DocumentStorage

    class RejectingCloudinaryStorage:
        def open(self, name, mode='rb'):
            raise OSError('Unauthorized')

    class FakeResponse:
        status_code = 200
        content = b'signed file content'

        def raise_for_status(self):
            return None

    package = types.ModuleType('cloudinary_storage')
    storage_module = types.ModuleType('cloudinary_storage.storage')
    storage_module.RawMediaCloudinaryStorage = RejectingCloudinaryStorage
    storage_module.MediaCloudinaryStorage = RejectingCloudinaryStorage
    storage_module.VideoMediaCloudinaryStorage = RejectingCloudinaryStorage
    cloudinary_package = types.ModuleType('cloudinary')
    cloudinary_utils = types.ModuleType('cloudinary.utils')
    generated_urls = []

    def fake_private_download_url(public_id, extension, **options):
        generated_urls.append((public_id, extension, options['resource_type']))
        return f'https://example.test/{options["resource_type"]}/{public_id}.{extension}'

    def fake_get(url, timeout=30):
        return FakeResponse()

    cloudinary_utils.private_download_url = fake_private_download_url
    monkeypatch.setitem(sys.modules, 'cloudinary_storage', package)
    monkeypatch.setitem(sys.modules, 'cloudinary_storage.storage', storage_module)
    monkeypatch.setitem(sys.modules, 'cloudinary', cloudinary_package)
    monkeypatch.setitem(sys.modules, 'cloudinary.utils', cloudinary_utils)
    monkeypatch.setattr('requests.get', fake_get)
    settings.CLOUDINARY_URL = 'cloudinary://key:secret@example'

    storage = DocumentStorage()
    file_obj = storage.open('media/documents/2026/04/rapport.pdf', 'rb')

    assert file_obj.read() == b'signed file content'
    assert generated_urls[0] == ('media/documents/2026/04/rapport.pdf', 'pdf', 'raw')


def test_open_document_file_maps_storage_read_error_to_404():
    from apps.documents.views import _open_document_file_or_404

    class FakeFile:
        def open(self, mode='rb'):
            raise OSError('remote file unavailable')

    class FakeDocument:
        pk = 42
        file_name = 'archive.zip'
        file = FakeFile()

    with pytest.raises(Http404):
        _open_document_file_or_404(FakeDocument())


@pytest.mark.django_db
def test_document_upload_handles_cloudinary_zip_rejection(authenticated_client, monkeypatch):
    from apps.documents.models import Document

    class FakeCloudinaryBadRequest(Exception):
        pass

    FakeCloudinaryBadRequest.__module__ = 'cloudinary.exceptions'

    def reject_save(self, *args, **kwargs):
        raise FakeCloudinaryBadRequest('Unsupported ZIP file')

    monkeypatch.setattr(Document, 'save', reject_save)
    upload = SimpleUploadedFile('archive.zip', b'PK\x03\x04test', content_type='application/zip')

    response = authenticated_client.post(
        reverse('documents:upload'),
        {
            'title': 'Archive',
            'description': '',
            'source': Document.Source.MANUAL,
            'tags': '',
            'visibility': Document.Visibility.STAFF,
            'file': upload,
        },
    )

    messages = [str(message) for message in get_messages(response.wsgi_request)]
    assert response.status_code == 200
    assert not Document.objects.exists()
    assert any('archive.zip' in message and 'stockage distant' in message for message in messages)
