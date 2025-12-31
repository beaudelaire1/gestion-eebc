from django.db import models
from django.conf import settings


class Member(models.Model):
    """
    Modèle représentant un membre de l'église.
    Peut être lié ou non à un compte utilisateur.
    """
    
    class Status(models.TextChoices):
        ACTIF = 'actif', 'Actif'
        INACTIF = 'inactif', 'Inactif'
        VISITEUR = 'visiteur', 'Visiteur'
        TRANSFERE = 'transfere', 'Transféré'
    
    class MaritalStatus(models.TextChoices):
        CELIBATAIRE = 'celibataire', 'Célibataire'
        MARIE = 'marie', 'Marié(e)'
        DIVORCE = 'divorce', 'Divorcé(e)'
        VEUF = 'veuf', 'Veuf/Veuve'
    
    # Lien optionnel vers un compte utilisateur
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='member_profile',
        verbose_name="Compte utilisateur"
    )
    
    # Identité
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="Date de naissance")
    gender = models.CharField(
        max_length=10,
        choices=[('M', 'Masculin'), ('F', 'Féminin')],
        blank=True,
        verbose_name="Genre"
    )
    photo = models.ImageField(upload_to='members/photos/', blank=True, null=True, verbose_name="Photo")
    
    # Contact
    email = models.EmailField(blank=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    address = models.TextField(blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="Code postal")
    
    # Situation
    marital_status = models.CharField(
        max_length=15,
        choices=MaritalStatus.choices,
        blank=True,
        verbose_name="Situation familiale"
    )
    profession = models.CharField(max_length=100, blank=True, verbose_name="Profession")
    
    # Église
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ACTIF,
        verbose_name="Statut"
    )
    date_joined = models.DateField(blank=True, null=True, verbose_name="Date d'arrivée")
    is_baptized = models.BooleanField(default=False, verbose_name="Baptisé(e)")
    baptism_date = models.DateField(blank=True, null=True, verbose_name="Date de baptême")
    
    # Métadonnées
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Membre"
        verbose_name_plural = "Membres"
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        if self.date_of_birth:
            from datetime import date
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None

