"""
Migration pour ajouter soft-delete à FinancialTransaction.
Permet la récupération des données en cas d'erreur.
"""

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),  # À adapter selon la dernière migration
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Ajouter les champs de soft-delete
        migrations.AddField(
            model_name='financialtransaction',
            name='is_deleted',
            field=models.BooleanField(default=False, verbose_name='Supprimé'),
        ),
        migrations.AddField(
            model_name='financialtransaction',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Date de suppression'),
        ),
        migrations.AddField(
            model_name='financialtransaction',
            name='deleted_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='deleted_transactions',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Supprimé par'
            ),
        ),
        
        # Ajouter un index sur is_deleted pour les performances
        migrations.AddIndex(
            model_name='financialtransaction',
            index=models.Index(fields=['is_deleted'], name='financial_deleted_idx'),
        ),
        
        # Ajouter un index composé pour les requêtes courantes
        migrations.AddIndex(
            model_name='financialtransaction',
            index=models.Index(fields=['is_deleted', 'status'], name='financial_deleted_status_idx'),
        ),
    ]
