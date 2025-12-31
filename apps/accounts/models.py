from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Modèle utilisateur personnalisé pour Gestion EEBC.
    Permet d'ajouter des rôles et des informations supplémentaires.
    """
    
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrateur'
        RESPONSABLE_CLUB = 'responsable_club', 'Responsable Club Biblique'
        MONITEUR = 'moniteur', 'Moniteur'
        CHAUFFEUR = 'chauffeur', 'Chauffeur'
        RESPONSABLE_GROUPE = 'responsable_groupe', 'Responsable de Groupe'
        MEMBRE = 'membre', 'Membre'
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBRE,
        verbose_name="Rôle"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Téléphone"
    )
    photo = models.ImageField(
        upload_to='users/photos/',
        blank=True,
        null=True,
        verbose_name="Photo"
    )
    date_joined_church = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date d'arrivée à l'église"
    )
    
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.get_full_name() or self.username}"
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser
    
    @property
    def is_responsable_club(self):
        return self.role == self.Role.RESPONSABLE_CLUB or self.is_admin
    
    @property
    def is_moniteur(self):
        return self.role == self.Role.MONITEUR or self.is_responsable_club
    
    @property
    def is_chauffeur(self):
        return self.role == self.Role.CHAUFFEUR or self.is_admin
    
    @property
    def is_responsable_groupe(self):
        return self.role == self.Role.RESPONSABLE_GROUPE or self.is_admin

