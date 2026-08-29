from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0009_alter_budgetforecast_scenario'),
    ]

    operations = [
        migrations.AddField(
            model_name='onlinedonation',
            name='receipt_email_attempts',
            field=models.PositiveSmallIntegerField(default=0, verbose_name="Tentatives d'envoi du reçu"),
        ),
        migrations.AddField(
            model_name='onlinedonation',
            name='receipt_email_last_error',
            field=models.TextField(blank=True, verbose_name="Dernière erreur d'envoi du reçu"),
        ),
        migrations.AddField(
            model_name='onlinedonation',
            name='receipt_email_sent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Reçu email envoyé le'),
        ),
    ]
