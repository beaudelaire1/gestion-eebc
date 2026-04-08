"""
Tests pour l'app imports — modèle ImportLog.
"""
import pytest
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
