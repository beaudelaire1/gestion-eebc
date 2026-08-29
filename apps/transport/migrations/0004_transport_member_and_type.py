from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0005_geocodedaddress'),
        ('transport', '0003_transportrequest_trans_req_date_time_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='transportrequest',
            name='requester_member',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name='transport_requests',
                to='members.member',
                verbose_name='Membre demandeur',
                help_text="Lié automatiquement si le demandeur est connecté",
            ),
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='request_type',
            field=models.CharField(
                choices=[
                    ('culte', 'Culte du dimanche'),
                    ('evenement', 'Événement'),
                    ('club', 'Club biblique / Jeunesse'),
                    ('covoiturage', 'Covoiturage entre membres'),
                    ('autre', 'Autre'),
                ],
                default='culte',
                max_length=15,
                verbose_name='Type de demande',
            ),
        ),
    ]
