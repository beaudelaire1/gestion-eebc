from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0008_budgetforecast_forecastline'),
    ]

    operations = [
        migrations.AlterField(
            model_name='budgetforecast',
            name='scenario',
            field=models.CharField(
                choices=[
                    ('realiste', 'Réaliste'),
                    ('realise', 'Réalisé'),
                    ('optimiste', 'Optimiste'),
                    ('pessimiste', 'Pessimiste'),
                ],
                default='realiste',
                max_length=15,
                verbose_name='Scénario',
            ),
        ),
    ]