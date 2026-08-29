from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0005_driverlivelocation'),
    ]

    operations = [
        migrations.AddField(
            model_name='transportrequest',
            name='pickup_latitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name='Latitude prise en charge'),
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='pickup_longitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name='Longitude prise en charge'),
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='pickup_location_source',
            field=models.CharField(choices=[('postal_address', 'Adresse postale'), ('requester_gps', 'GPS demandeur')], default='postal_address', max_length=20, verbose_name='Source position prise en charge'),
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='pickup_location_updated_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Position prise en charge mise à jour le'),
        ),
    ]