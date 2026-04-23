from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial_core'),
        ('bibleclub', '0003_remove_child_parent1_email_remove_child_parent1_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='child',
            name='family',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name='bibleclub_children',
                to='core.family',
                verbose_name='Famille',
            ),
        ),
    ]
