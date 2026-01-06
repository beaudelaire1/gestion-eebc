# Generated manually to add is_pinned field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('communication', '0003_unsubscribepreference_alter_emaillog_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcement',
            name='is_pinned',
            field=models.BooleanField(default=False, verbose_name='Épinglée'),
        ),
        migrations.AlterModelOptions(
            name='announcement',
            options={'ordering': ['-is_pinned', '-created_at'], 'verbose_name': 'Annonce', 'verbose_name_plural': 'Annonces'},
        ),
    ]
