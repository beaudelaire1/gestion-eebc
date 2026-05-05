from django.db import models
from django.conf import settings
from django.utils import timezone


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

    class RequestType(models.TextChoices):
        CULTE = 'culte', 'Culte du dimanche'
        EVENEMENT = 'evenement', 'Événement'
        CLUB = 'club', 'Club biblique / Jeunesse'
        COVOITURAGE = 'covoiturage', 'Covoiturage entre membres'
        AUTRE = 'autre', 'Autre'

    class PickupLocationSource(models.TextChoices):
        POSTAL_ADDRESS = 'postal_address', 'Adresse postale'
        REQUESTER_GPS = 'requester_gps', 'GPS demandeur'

    # Lien optionnel vers un membre demandeur (covoiturage / transport membre)
    requester_member = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transport_requests',
        verbose_name="Membre demandeur",
        help_text="Lié automatiquement si le demandeur est connecté",
    )

    request_type = models.CharField(
        max_length=15,
        choices=RequestType.choices,
        default=RequestType.CULTE,
        verbose_name="Type de demande",
    )

    requester_name = models.CharField(max_length=200, verbose_name="Demandeur")
    requester_phone = models.CharField(max_length=20, verbose_name="Téléphone")
    requester_email = models.EmailField(blank=True, verbose_name="Email du demandeur")
    pickup_address = models.TextField(verbose_name="Adresse de prise en charge")
    pickup_city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ville de prise en charge",
    )
    pickup_postal_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Code postal de prise en charge",
    )
    pickup_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Latitude prise en charge",
    )
    pickup_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Longitude prise en charge",
    )
    pickup_location_source = models.CharField(
        max_length=20,
        choices=PickupLocationSource.choices,
        default=PickupLocationSource.POSTAL_ADDRESS,
        verbose_name="Source position prise en charge",
    )
    pickup_location_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Position prise en charge mise à jour le",
    )
    
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
        indexes = [
            models.Index(fields=['event_date', 'event_time'], name='trans_req_date_time_idx'),
        ]
    
    def __str__(self):
        return f"{self.requester_name} - {self.event_date}"


class DriverLiveLocation(models.Model):
    """Dernière position GPS connue d'un chauffeur pour une demande donnée."""

    transport_request = models.OneToOneField(
        TransportRequest,
        on_delete=models.CASCADE,
        related_name='live_location',
        verbose_name="Demande de transport",
    )
    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.CASCADE,
        related_name='live_locations',
        verbose_name="Chauffeur",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="Latitude")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="Longitude")
    speed_kmh = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Vitesse (km/h)",
    )
    accuracy_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Précision (m)",
    )
    heading_deg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Cap (degrés)",
    )
    recorded_at = models.DateTimeField(default=timezone.now, verbose_name="Horodatage GPS")
    is_active = models.BooleanField(default=True, verbose_name="Suivi actif")
    started_at = models.DateTimeField(default=timezone.now, verbose_name="Suivi démarré")
    stopped_at = models.DateTimeField(null=True, blank=True, verbose_name="Suivi arrêté")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Position live chauffeur"
        verbose_name_plural = "Positions live chauffeurs"
        indexes = [
            models.Index(fields=['driver', 'updated_at'], name='driver_live_driver_upd_idx'),
            models.Index(fields=['transport_request', 'is_active'], name='driver_live_req_active_idx'),
        ]

    def __str__(self):
        return f"Live {self.driver.user.get_full_name()} - demande #{self.transport_request_id}"

