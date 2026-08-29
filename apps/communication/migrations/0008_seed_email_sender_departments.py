"""Crée les départements expéditeurs initiaux de l'éditeur d'e-mails."""
from django.db import migrations

DEPARTMENTS = [
    {'name': 'Multimédia & technique', 'from_email': 'multimedia@eglise-ebc.org', 'phone': '', 'order': 1},
    {'name': 'Communication', 'from_email': 'communication@eglise-ebc.org', 'phone': '+594 694 93 50 56', 'order': 2},
    {'name': 'Secrétariat', 'from_email': 'secretariat@eglise-ebc.org', 'phone': '+594 694 47 28 06', 'order': 3},
    {'name': 'Direction', 'from_email': 'contact@eglise-ebc.org', 'phone': '+594 694 41 89 90', 'order': 4},
]


def create_departments(apps, schema_editor):
    EmailSenderDepartment = apps.get_model('communication', 'EmailSenderDepartment')
    for dept in DEPARTMENTS:
        EmailSenderDepartment.objects.get_or_create(name=dept['name'], defaults=dept)


def remove_departments(apps, schema_editor):
    EmailSenderDepartment = apps.get_model('communication', 'EmailSenderDepartment')
    EmailSenderDepartment.objects.filter(name__in=[d['name'] for d in DEPARTMENTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('communication', '0007_emailsenderdepartment'),
    ]

    operations = [
        migrations.RunPython(create_departments, remove_departments),
    ]
