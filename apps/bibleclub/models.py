from django.db import models
from django.conf import settings
from django.utils import timezone


class AgeGroup(models.Model):
    """
    Tranche d'âge pour le club biblique.
    Ex : 3-5 ans, 6-8 ans, 9-12 ans
    """
    name = models.CharField(max_length=50, verbose_name="Nom de la tranche")
    min_age = models.PositiveIntegerField(verbose_name="Âge minimum")
    max_age = models.PositiveIntegerField(verbose_name="Âge maximum")
    description = models.TextField(blank=True, verbose_name="Description")
    color = models.CharField(max_length=7, default="#0d6efd", verbose_name="Couleur")
    
    class Meta:
        verbose_name = "Tranche d'âge"
        verbose_name_plural = "Tranches d'âge"
        ordering = ['min_age']
        constraints = [
            models.CheckConstraint(
                check=models.Q(min_age__lt=models.F('max_age')),
                name='min_age_less_than_max_age'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.min_age}-{self.max_age} ans)"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.min_age and self.max_age and self.min_age >= self.max_age:
            raise ValidationError("L'âge minimum doit être inférieur à l'âge maximum.")


class BibleClass(models.Model):
    """
    Classe du club biblique (sans nom, identifiée par tranche d'âge).
    """
    age_group = models.ForeignKey(
        AgeGroup,
        on_delete=models.CASCADE,
        related_name='classes',
        verbose_name="Tranche d'âge"
    )
    
    room = models.CharField(max_length=50, blank=True, verbose_name="Salle")
    max_capacity = models.PositiveIntegerField(default=15, verbose_name="Capacité max")
    
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Classe"
        verbose_name_plural = "Classes"
        ordering = ['age_group__min_age']
    
    def __str__(self):
        suffix = f" - {self.room}" if self.room else ""
        return f"{self.age_group.name}{suffix}"
    
    @property
    def children_count(self):
        return self.children.filter(is_active=True).count()
    
    @property
    def monitors_list(self):
        return self.monitors.filter(is_active=True)


class Monitor(models.Model):
    """
    Moniteur du club biblique.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='monitor_profile',
        verbose_name="Utilisateur"
    )
    
    bible_class = models.ForeignKey(
        BibleClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='monitors',
        verbose_name="Classe assignée"
    )
    
    is_lead = models.BooleanField(default=False, verbose_name="Moniteur principal")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Moniteur"
        verbose_name_plural = "Moniteurs"
        ordering = ['-is_lead', 'user__last_name']
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Child(models.Model):
    """
    Enfant inscrit au club biblique.
    """
    # Identité
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    date_of_birth = models.DateField(verbose_name="Date de naissance")
    gender = models.CharField(
        max_length=1,
        choices=[('M', 'Masculin'), ('F', 'Féminin')],
        verbose_name="Genre"
    )
    photo = models.ImageField(upload_to='bibleclub/children/', blank=True, null=True, verbose_name="Photo")
    
    # Classe
    bible_class = models.ForeignKey(
        BibleClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Classe"
    )
    
    # Contacts parents
    father_name = models.CharField(max_length=200, verbose_name="Nom du père")
    father_phone = models.CharField(max_length=20, verbose_name="Téléphone du père")
    father_email = models.EmailField(blank=True, verbose_name="Email du père")
    
    mother_name = models.CharField(max_length=200, blank=True, verbose_name="Nom de la mère")
    mother_phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone de la mère")
    mother_email = models.EmailField(blank=True, verbose_name="Email de la mère")
    
    # Contact d'urgence
    emergency_contact = models.CharField(max_length=200, blank=True, verbose_name="Contact d'urgence")
    emergency_phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone d'urgence")
    
    # Informations médicales
    allergies = models.TextField(blank=True, verbose_name="Allergies")
    medical_notes = models.TextField(blank=True, verbose_name="Notes médicales")
    
    # Transport
    needs_transport = models.BooleanField(default=False, verbose_name="Besoin de transport")
    pickup_address = models.TextField(blank=True, verbose_name="Adresse de ramassage")
    assigned_driver = models.ForeignKey(
        'transport.DriverProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_children',
        verbose_name="Chauffeur assigné"
    )
    
    # Statut
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    registration_date = models.DateField(auto_now_add=True, verbose_name="Date d'inscription")
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Enfant"
        verbose_name_plural = "Enfants"
        ordering = ['last_name', 'first_name']
    
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


class Session(models.Model):
    """
    Session/séance du club biblique (un dimanche).
    """
    date = models.DateField(unique=True, verbose_name="Date")
    theme = models.CharField(max_length=200, blank=True, verbose_name="Thème")
    notes = models.TextField(blank=True, verbose_name="Notes")
    is_cancelled = models.BooleanField(default=False, verbose_name="Annulée")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Session"
        verbose_name_plural = "Sessions"
        ordering = ['-date']
    
    def __str__(self):
        status = " (Annulée)" if self.is_cancelled else ""
        return f"Session du {self.date.strftime('%d/%m/%Y')}{status}"


class Attendance(models.Model):
    """
    Présence d'un enfant à une session.
    """
    class Status(models.TextChoices):
        PRESENT = 'present', 'Présent'
        ABSENT = 'absent', 'Absent'
        ABSENT_NOTIFIED = 'absent_notified', 'Absent (notifié)'
        LATE = 'late', 'En retard'
        EXCUSED = 'excused', 'Excusé'
    
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Session"
    )
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Enfant"
    )
    bible_class = models.ForeignKey(
        BibleClass,
        on_delete=models.SET_NULL,
        null=True,
        related_name='attendances',
        verbose_name="Classe"
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ABSENT,
        verbose_name="Statut"
    )
    
    check_in_time = models.TimeField(blank=True, null=True, verbose_name="Heure d'arrivée")
    check_out_time = models.TimeField(blank=True, null=True, verbose_name="Heure de départ")
    
    picked_up_by = models.CharField(max_length=200, blank=True, verbose_name="Récupéré par")
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_attendances',
        verbose_name="Enregistré par"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Présence"
        verbose_name_plural = "Présences"
        unique_together = ['session', 'child']
        ordering = ['child__last_name', 'child__first_name']
    
    def __str__(self):
        return f"{self.child} - {self.session.date} - {self.get_status_display()}"


class DriverCheckIn(models.Model):
    """
    Pointage du chauffeur pour le transport des enfants.
    """
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='driver_checkins',
        verbose_name="Session"
    )
    driver = models.ForeignKey(
        'transport.DriverProfile',
        on_delete=models.CASCADE,
        related_name='checkins',
        verbose_name="Chauffeur"
    )
    
    departure_time = models.TimeField(blank=True, null=True, verbose_name="Heure de départ")
    arrival_time = models.TimeField(blank=True, null=True, verbose_name="Heure d'arrivée église")
    return_departure_time = models.TimeField(blank=True, null=True, verbose_name="Heure départ retour")
    return_arrival_time = models.TimeField(blank=True, null=True, verbose_name="Heure arrivée retour")
    
    children_picked_up = models.ManyToManyField(
        Child,
        blank=True,
        related_name='transport_pickups',
        verbose_name="Enfants transportés"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Pointage Chauffeur"
        verbose_name_plural = "Pointages Chauffeurs"
        unique_together = ['session', 'driver']
    
    def __str__(self):
        return f"{self.driver} - {self.session.date}"

