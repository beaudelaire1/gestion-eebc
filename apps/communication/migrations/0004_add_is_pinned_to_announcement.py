# Generated manually to add is_pinned field
"""Ajout idempotent de ``Announcement.is_pinned``.

``0001_initial`` a été régénéré après coup avec ``is_pinned`` déjà déclaré sur
``Announcement``. Toute base créée à partir de cet initial possède donc la
colonne avant que cette migration ne s'exécute, et PostgreSQL rejette alors
l'``AddField`` brut :

    column "is_pinned" of relation "communication_announcement" already exists

SQLite tolère silencieusement le même cas, ce qui masque le problème hors
production. Les bases historiques créées avant la régénération de
``0001_initial`` ont, elles, réellement besoin de la colonne : le DDL n'est donc
appliqué que si l'introspection ne trouve pas la colonne. L'état du modèle est
identique dans les deux cas.
"""

from django.db import migrations, models


TABLE = 'communication_announcement'
COLUMN = 'is_pinned'


def add_column_if_missing(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        existing = {
            column.name
            for column in connection.introspection.get_table_description(cursor, TABLE)
        }

    if COLUMN in existing:
        return

    model = apps.get_model('communication', 'Announcement')
    schema_editor.add_field(model, model._meta.get_field(COLUMN))


class Migration(migrations.Migration):

    dependencies = [
        ('communication', '0003_unsubscribepreference_alter_emaillog_options_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Le retour arrière ne supprime pas la colonne : sur une base créée
            # depuis 0001_initial elle appartient à la création de la table.
            database_operations=[
                migrations.RunPython(add_column_if_missing, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='announcement',
                    name='is_pinned',
                    field=models.BooleanField(default=False, verbose_name='Épinglée'),
                ),
            ],
        ),
        migrations.AlterModelOptions(
            name='announcement',
            options={'ordering': ['-is_pinned', '-created_at'], 'verbose_name': 'Annonce', 'verbose_name_plural': 'Annonces'},
        ),
    ]
