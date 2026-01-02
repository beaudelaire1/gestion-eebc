from django.db import models
from django.conf import settings


class Department(models.Model):
    """
    Modèle représentant un département de l'église.
    """
    name = models.CharField(max_length=100, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Site d'appartenance (multi-sites)
    site = models.ForeignKey(
        'core.Site',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departments',
        verbose_name="Site"
    )
    
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_departments',
        verbose_name="Responsable"
    )
    
    members = models.ManyToManyField(
        'members.Member',
        blank=True,
        related_name='departments',
        verbose_name="Membres"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Département"
        verbose_name_plural = "Départements"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def member_count(self):
        return self.members.count()

