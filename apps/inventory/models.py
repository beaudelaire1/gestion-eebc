from django.db import models
from django.conf import settings


class Category(models.Model):
    """Catégorie de matériel."""
    name = models.CharField(max_length=100, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    
    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ActiveEquipmentManager(models.Manager):
    """Manager pour récupérer uniquement les équipements actifs."""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Equipment(models.Model):
    """
    Modèle représentant un équipement de l'église.
    """
    class Condition(models.TextChoices):
        NEW = 'new', 'Neuf'
        GOOD = 'good', 'Bon état'
        FAIR = 'fair', 'État moyen'
        MAINTENANCE = 'maintenance', 'En maintenance'
        BROKEN = 'broken', 'Hors service'
    
    name = models.CharField(max_length=200, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipment',
        verbose_name="Catégorie"
    )
    
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantité")
    
    condition = models.CharField(
        max_length=15,
        choices=Condition.choices,
        default=Condition.GOOD,
        verbose_name="État"
    )
    
    location = models.CharField(max_length=100, blank=True, verbose_name="Emplacement")
    purchase_date = models.DateField(blank=True, null=True, verbose_name="Date d'achat")
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Prix d'achat"
    )
    
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responsible_equipment',
        verbose_name="Responsable"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    photo = models.ImageField(upload_to='inventory/photos/', blank=True, null=True, verbose_name="Photo")
    
    # Soft delete field
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Managers
    objects = models.Manager()  # Manager par défaut (tous les équipements)
    active = ActiveEquipmentManager()  # Manager pour les équipements actifs
    
    class Meta:
        verbose_name = "Équipement"
        verbose_name_plural = "Équipements"
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_condition_display()})"
    
    def soft_delete(self):
        """Suppression logique de l'équipement."""
        self.is_active = False
        self.save()
    
    def restore(self):
        """Restauration d'un équipement supprimé."""
        self.is_active = True
        self.save()
    
    @property
    def needs_attention(self):
        """Retourne True si l'équipement nécessite une attention (mauvais état)."""
        return self.condition in [self.Condition.MAINTENANCE, self.Condition.BROKEN]

