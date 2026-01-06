from django.db import models
from django.conf import settings


class ImportLog(models.Model):
    """
    Journal des imports de données.
    """
    
    class ImportType(models.TextChoices):
        MEMBERS = 'members', 'Membres'
        CHILDREN = 'children', 'Enfants'
        EXPORT = 'export', 'Export'  # Nouveau type pour les exports
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        PROCESSING = 'processing', 'En cours'
        SUCCESS = 'success', 'Réussi'
        ERROR = 'error', 'Erreur'
        PARTIAL = 'partial', 'Partiel'
    
    import_type = models.CharField(
        max_length=20,
        choices=ImportType.choices,
        verbose_name="Type d'import"
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )
    
    file_name = models.CharField(max_length=255, verbose_name="Nom du fichier")
    file_path = models.FileField(upload_to='imports/', verbose_name="Fichier")
    
    # Statistiques
    total_rows = models.PositiveIntegerField(default=0, verbose_name="Lignes totales")
    processed_rows = models.PositiveIntegerField(default=0, verbose_name="Lignes traitées")
    success_rows = models.PositiveIntegerField(default=0, verbose_name="Lignes réussies")
    error_rows = models.PositiveIntegerField(default=0, verbose_name="Lignes en erreur")
    
    # Messages
    error_log = models.TextField(blank=True, verbose_name="Journal d'erreurs")
    success_log = models.TextField(blank=True, verbose_name="Journal de succès")
    
    # Métadonnées
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Importé par"
    )
    
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Démarré à")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Terminé à")
    
    class Meta:
        verbose_name = "Journal d'import"
        verbose_name_plural = "Journaux d'import"
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.get_import_type_display()} - {self.file_name} ({self.get_status_display()})"
    
    @property
    def duration(self):
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def success_rate(self):
        if self.total_rows > 0:
            return (self.success_rows / self.total_rows) * 100
        return 0