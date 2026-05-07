import uuid

from django.db import migrations, models


def populate_tracking_tokens(apps, schema_editor):
    TransportRequest = apps.get_model('transport', 'TransportRequest')
    for transport_request in TransportRequest.objects.filter(tracking_token__isnull=True).only('pk'):
        transport_request.tracking_token = uuid.uuid4()
        transport_request.save(update_fields=['tracking_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0008_add_en_route_arriving_statuses'),
    ]

    operations = [
        migrations.AddField(
            model_name='transportrequest',
            name='tracking_token',
            field=models.UUIDField(
                db_index=True,
                editable=False,
                help_text='Identifiant UUID utilisé pour le lien de suivi passager (sans authentification).',
                null=True,
                verbose_name='Token de suivi public',
            ),
        ),
        migrations.RunPython(populate_tracking_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='transportrequest',
            name='tracking_token',
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                help_text='Identifiant UUID utilisé pour le lien de suivi passager (sans authentification).',
                unique=True,
                verbose_name='Token de suivi public',
            ),
        ),
    ]