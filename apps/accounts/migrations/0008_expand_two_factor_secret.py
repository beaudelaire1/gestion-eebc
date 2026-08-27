from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0007_alter_user_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='two_factor_secret',
            field=models.CharField(
                blank=True,
                help_text='Secret TOTP chiffré au repos',
                max_length=255,
                verbose_name='Clé secrète 2FA',
            ),
        ),
    ]
