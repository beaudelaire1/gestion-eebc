# Generated migration for new transport request statuses

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0007_transportrequest_pickup_city_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transportrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'En attente'),
                    ('confirmed', 'Confirmé'),
                    ('en_route', 'En route'),
                    ('arriving', 'Arrive bientôt'),
                    ('completed', 'Effectué'),
                    ('cancelled', 'Annulé')
                ],
                default='pending',
                max_length=15,
                verbose_name='Statut'
            ),
        ),
    ]
