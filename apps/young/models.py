from django.db import models
from django.conf import settings
from django.utils import timezone


class YouthGroup(models.Model):
    """
    Groupe / tranche d'âge pour la jeunesse.
    Ex : Ados (13-17 ans), Jeunes adultes (18-25 ans)
    """
    name = models.CharField(max_length=100, verbose_name="Nom du groupe")
    min_age = models.PositiveIntegerField(verbose_name="Âge minimum")
    max_age = models.PositiveIntegerField(verbose_name="Âge maximum")
    description = models.TextField(blank=True, verbose_name="Description")
    color = models.CharField(max_length=7, default="#6366f1", verbose_name="Couleur")
    is_active = models.BooleanField(default=True, verbose_name="Actif")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Groupe de jeunesse"
        verbose_name_plural = "Groupes de jeunesse"
        ordering = ['min_age']

    def __str__(self):
        return f"{self.name} ({self.min_age}-{self.max_age} ans)"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.min_age and self.max_age and self.min_age >= self.max_age:
            raise ValidationError("L'âge minimum doit être inférieur à l'âge maximum.")

    @property
    def members_count(self):
        return self.young_members.filter(is_active=True).count()


class YoungMember(models.Model):
    """
    Jeune inscrit au ministère de la jeunesse.
    """

    class Status(models.TextChoices):
        ACTIF = 'actif', 'Actif'
        INACTIF = 'inactif', 'Inactif'
        VISITEUR = 'visiteur', 'Visiteur'

    class Gender(models.TextChoices):
        MASCULIN = 'M', 'Masculin'
        FEMININ = 'F', 'Féminin'

    # Identité
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    date_of_birth = models.DateField(verbose_name="Date de naissance")
    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        verbose_name="Genre",
    )
    photo = models.ImageField(
        upload_to='young/photos/',
        blank=True, null=True,
        verbose_name="Photo",
    )

    # Rattachement
    site = models.ForeignKey(
        'core.Site',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='young_members',
        verbose_name="Site",
    )
    group = models.ForeignKey(
        YouthGroup,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='young_members',
        verbose_name="Groupe",
    )

    # Lien famille / membre existant
    family = models.ForeignKey(
        'core.Family',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='young_members',
        verbose_name="Famille",
    )
    linked_member = models.OneToOneField(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='young_profile',
        verbose_name="Fiche membre liée",
        help_text="Lier à une fiche membre existante (optionnel)",
    )

    # Contact
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.TextField(blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="Code postal")

    # Contacts parents / responsable légal
    parent_name = models.CharField(
        max_length=200, blank=True,
        verbose_name="Nom du parent / responsable légal",
    )
    parent_phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone parent")
    parent_email = models.EmailField(blank=True, verbose_name="Email parent")

    # Contact d'urgence
    emergency_contact = models.CharField(max_length=200, blank=True, verbose_name="Contact d'urgence")
    emergency_phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone d'urgence")

    # Infos médicales
    allergies = models.TextField(blank=True, verbose_name="Allergies")
    medical_notes = models.TextField(blank=True, verbose_name="Notes médicales")

    # Vie spirituelle
    is_baptized = models.BooleanField(default=False, verbose_name="Baptisé(e)")
    baptism_date = models.DateField(blank=True, null=True, verbose_name="Date de baptême")
    is_born_again = models.BooleanField(default=False, verbose_name="Né(e) de nouveau")
    conversion_date = models.DateField(blank=True, null=True, verbose_name="Date de conversion")

    # Transport
    needs_transport = models.BooleanField(default=False, verbose_name="Besoin de transport")
    pickup_address = models.TextField(blank=True, verbose_name="Adresse de ramassage")
    assigned_driver = models.ForeignKey(
        'transport.DriverProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_young',
        verbose_name="Chauffeur assigné",
    )

    # Statut
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ACTIF,
        verbose_name="Statut",
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    registration_date = models.DateField(auto_now_add=True, verbose_name="Date d'inscription")

    notes = models.TextField(blank=True, verbose_name="Notes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Jeune"
        verbose_name_plural = "Jeunes"
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['site']),
            models.Index(fields=['is_baptized']),
            models.Index(fields=['group']),
            models.Index(fields=['last_name', 'first_name']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def is_minor(self):
        return self.age < 18


class YouthEvent(models.Model):
    """
    Activité / rencontre de jeunesse (réunion du samedi, sortie, camp, etc.).
    """

    class EventType(models.TextChoices):
        REUNION = 'reunion', 'Réunion'
        SORTIE = 'sortie', 'Sortie'
        CAMP = 'camp', 'Camp'
        FORMATION = 'formation', 'Formation'
        SERVICE = 'service', 'Service communautaire'
        AUTRE = 'autre', 'Autre'

    title = models.CharField(max_length=200, verbose_name="Titre")
    event_type = models.CharField(
        max_length=15,
        choices=EventType.choices,
        default=EventType.REUNION,
        verbose_name="Type",
    )
    date = models.DateField(verbose_name="Date")
    start_time = models.TimeField(blank=True, null=True, verbose_name="Heure de début")
    end_time = models.TimeField(blank=True, null=True, verbose_name="Heure de fin")
    location = models.CharField(max_length=200, blank=True, verbose_name="Lieu")
    description = models.TextField(blank=True, verbose_name="Description")
    is_cancelled = models.BooleanField(default=False, verbose_name="Annulé")

    site = models.ForeignKey(
        'core.Site',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='youth_events',
        verbose_name="Site",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_youth_events',
        verbose_name="Créé par",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Activité jeunesse"
        verbose_name_plural = "Activités jeunesse"
        ordering = ['-date']

    def __str__(self):
        status = " (Annulé)" if self.is_cancelled else ""
        return f"{self.title} — {self.date.strftime('%d/%m/%Y')}{status}"


class YouthAttendance(models.Model):
    """
    Présence d'un jeune à une activité.
    """

    class Status(models.TextChoices):
        PRESENT = 'present', 'Présent'
        ABSENT = 'absent', 'Absent'
        EXCUSE = 'excuse', 'Excusé'
        RETARD = 'retard', 'En retard'

    event = models.ForeignKey(
        YouthEvent,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Activité",
    )
    young_member = models.ForeignKey(
        YoungMember,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Jeune",
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ABSENT,
        verbose_name="Statut",
    )
    check_in_time = models.TimeField(blank=True, null=True, verbose_name="Heure d'arrivée")

    transported = models.BooleanField(default=False, verbose_name="Transporté par l'église")

    notes = models.TextField(blank=True, verbose_name="Notes")

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='recorded_youth_attendances',
        verbose_name="Enregistré par",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Présence jeunesse"
        verbose_name_plural = "Présences jeunesse"
        unique_together = ['event', 'young_member']
        ordering = ['young_member__last_name', 'young_member__first_name']

    def __str__(self):
        return f"{self.young_member} — {self.event.date} — {self.get_status_display()}"
