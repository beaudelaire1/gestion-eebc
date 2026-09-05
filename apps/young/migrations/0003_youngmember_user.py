import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("young", "0002_youthevent_youth_event_date_idx"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="youngmember",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="young_profile",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Compte utilisateur du jeune",
                help_text="Compte optionnel, indépendant de l'appartenance à l'église.",
            ),
        ),
    ]
