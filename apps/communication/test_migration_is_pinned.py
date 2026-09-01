"""Régression : la migration 0004 ne doit jamais réémettre le DDL de is_pinned.

``0001_initial`` déclare déjà ``Announcement.is_pinned``. Sur PostgreSQL, un
``AddField`` brut échoue alors avec ``column "is_pinned" ... already exists`` et
bloque tout le déploiement. SQLite tolère le doublon, donc seul un test explicite
protège cette invariance quel que soit le moteur.
"""

import importlib

import pytest
from django.apps import apps as global_apps
from django.db import connection


MIGRATION = importlib.import_module(
    'apps.communication.migrations.0004_add_is_pinned_to_announcement'
)


def _columns():
    with connection.cursor() as cursor:
        return {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, MIGRATION.TABLE
            )
        }


class _RecordingSchemaEditor:
    """Éditeur minimal : seule compte l'absence d'appel à add_field."""

    def __init__(self):
        self.connection = connection
        self.calls = []

    def add_field(self, *args, **kwargs):
        self.calls.append(args)


@pytest.mark.django_db
def test_migration_skips_ddl_when_column_already_exists():
    assert MIGRATION.COLUMN in _columns()

    schema_editor = _RecordingSchemaEditor()
    MIGRATION.add_column_if_missing(global_apps, schema_editor)

    assert schema_editor.calls == [], (
        'La migration a tenté de recréer une colonne existante.'
    )


@pytest.mark.django_db(transaction=True)
def test_migration_adds_the_column_when_it_is_missing():
    model = global_apps.get_model('communication', 'Announcement')
    field = model._meta.get_field(MIGRATION.COLUMN)

    with connection.schema_editor() as schema_editor:
        schema_editor.remove_field(model, field)
    assert MIGRATION.COLUMN not in _columns()

    try:
        with connection.schema_editor() as schema_editor:
            MIGRATION.add_column_if_missing(global_apps, schema_editor)
        assert MIGRATION.COLUMN in _columns()
    finally:
        if MIGRATION.COLUMN not in _columns():
            with connection.schema_editor() as schema_editor:
                schema_editor.add_field(model, field)
