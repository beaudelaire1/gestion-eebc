"""
Tests pour l'app imports — modèle ImportLog.
"""
import pytest
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import User
from apps.imports.models import ImportLog


@pytest.mark.django_db
class TestImportLog:

    def test_create_import_log(self):
        from apps.accounts.models import User
        user = User.objects.create_user(
            username='importuser', email='import@example.com', password='Pass123!'
        )
        log = ImportLog.objects.create(
            imported_by=user,
            file_name='members_2026.xlsx',
        )
        assert log.pk is not None
        assert str(log)

    def test_import_file_uses_filesystem_storage(self):
        storage = ImportLog._meta.get_field('file_path').storage
        assert isinstance(storage, FileSystemStorage)


@pytest.mark.django_db
class TestImportCreateView:

    def test_create_import_accepts_xlsx_without_server_error(self, client, monkeypatch):
        user = User.objects.create_user(
            username='admin_import',
            email='admin.import@example.com',
            password='Pass123!',
            role='admin',
        )
        client.force_login(user)

        def _noop_process_import(self):
            return None

        monkeypatch.setattr('apps.imports.views.ExcelImportService.process_import', _noop_process_import)

        uploaded = SimpleUploadedFile(
            'children.xlsx',
            b'fake-xlsx-content',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        response = client.post(
            reverse('imports:create'),
            data={
                'import_type': ImportLog.ImportType.CHILDREN,
                'file_path': uploaded,
            },
        )

        assert response.status_code == 302
        assert ImportLog.objects.count() == 1
