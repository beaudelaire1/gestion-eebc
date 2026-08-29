from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0005_geocodedaddress'),
        ('bibleclub', '0004_child_family'),
    ]

    operations = [
        migrations.AddField(
            model_name='child',
            name='linked_member',
            field=models.OneToOneField(
                blank=True,
                help_text="Fiche membre correspondante (créée automatiquement lors du rattachement à une famille)",
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name='bibleclub_profile',
                to='members.member',
                verbose_name='Fiche membre liée',
            ),
        ),
    ]
