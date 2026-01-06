from django.db import models
from django.conf import settings


class DriverProfile(models.Model):
    """
    Profil d'un chauffeur bénévole.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='driver_profile',
        verbose_name="Utilisateur"
    )
    
    vehicle_type = models.CharField(max_length=50, verbose_name="Type de véhicule")
    vehicle_model = models.CharField(max_length=100, blank=True, verbose_name="Modèle")
    license_plate = models.CharField(max_length=20, blank=True, verbose_name="Immatriculation")
    
    capacity = models.PositiveIntegerField(
        default=4,
        verbose_name="Capacité (passagers)"
    )
    
    zone = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Zone desservie",
        help_text="Quartier ou zone géographique couverte"
    )
    
    is_available = models.BooleanField(default=True, verbose_name="Disponible")
    available_sunday = models.BooleanField(default=True, verbose_name="Disponible le dimanche")
    available_week = models.BooleanField(default=False, verbose_name="Disponible en semaine")
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Profil Chauffeur"
        verbose_name_plural = "Profils Chauffeurs"
        ordering = ['user__last_name', 'user__first_name']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.vehicle_type}"


class TransportRequest(models.Model):
    """
    Demande de transport.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        CONFIRMED = 'confirmed', 'Confirmé'
        COMPLETED = 'completed', 'Effectué'
        CANCELLED = 'cancelled', 'Annulé'
    
    requester_name = models.CharField(max_length=200, verbose_name="Demandeur")
    requester_phone = models.CharField(max_length=20, verbose_name="Téléphone")
    requester_email = models.EmailField(blank=True, verbose_name="Email du demandeur")
    pickup_address = models.TextField(verbose_name="Adresse de prise en charge")
    
    event_date = models.DateField(verbose_name="Date")
    event_time = models.TimeField(verbose_name="Heure")
    event_name = models.CharField(max_length=200, blank=True, verbose_name="Événement")
    
    passengers_count = models.PositiveIntegerField(default=1, verbose_name="Nombre de passagers")
    
    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transport_requests',
        verbose_name="Chauffeur assigné"
    )
    
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Demande de Transport"
        verbose_name_plural = "Demandes de Transport"
        ordering = ['-event_date', '-event_time']
    
    def __str__(self):
        return f"{self.requester_name} - {self.event_date}"

