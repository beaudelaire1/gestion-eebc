from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0004_transport_member_and_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='DriverLiveLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9, verbose_name='Latitude')),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9, verbose_name='Longitude')),
                ('speed_kmh', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='Vitesse (km/h)')),
                ('accuracy_m', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='Précision (m)')),
                ('heading_deg', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='Cap (degrés)')),
                ('recorded_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Horodatage GPS')),
                ('is_active', models.BooleanField(default=True, verbose_name='Suivi actif')),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Suivi démarré')),
                ('stopped_at', models.DateTimeField(blank=True, null=True, verbose_name='Suivi arrêté')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='live_locations', to='transport.driverprofile', verbose_name='Chauffeur')),
                ('transport_request', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='live_location', to='transport.transportrequest', verbose_name='Demande de transport')),
            ],
            options={
                'verbose_name': 'Position live chauffeur',
                'verbose_name_plural': 'Positions live chauffeurs',
            },
        ),
        migrations.AddIndex(
            model_name='driverlivelocation',
            index=models.Index(fields=['driver', 'updated_at'], name='driver_live_driver_upd_idx'),
        ),
        migrations.AddIndex(
            model_name='driverlivelocation',
            index=models.Index(fields=['transport_request', 'is_active'], name='driver_live_req_active_idx'),
        ),
    ]
