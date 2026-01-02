from django.db import models
from django.conf import settings


class Group(models.Model):
    """
    Groupe de l'église (Jeunesse, Chorale, The Ray of Sunshine, etc.)
    """
    class GroupType(models.TextChoices):
        YOUTH = 'youth', 'Jeunesse'
        CHOIR = 'choir', 'Chorale'
        PRAYER = 'prayer', 'Groupe de prière'
        STUDY = 'study', 'Groupe d\'étude'
        SERVICE = 'service', 'Service'
        OTHER = 'other', 'Autre'
    
    name = models.CharField(max_length=100, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Site d'appartenance (multi-sites)
    site = models.ForeignKey(
        'core.Site',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='groups',
        verbose_name="Site"
    )
    
    group_type = models.CharField(
        max_length=15,
        choices=GroupType.choices,
        default=GroupType.OTHER,
        verbose_name="Type"
    )
    
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_groups',
        verbose_name="Responsable"
    )
    
    members = models.ManyToManyField(
        'members.Member',
        blank=True,
        related_name='groups',
        verbose_name="Membres"
    )
    
    # Horaires récurrents
    meeting_day = models.CharField(
        max_length=15,
        choices=[
            ('monday', 'Lundi'),
            ('tuesday', 'Mardi'),
            ('wednesday', 'Mercredi'),
            ('thursday', 'Jeudi'),
            ('friday', 'Vendredi'),
            ('saturday', 'Samedi'),
            ('sunday', 'Dimanche'),
        ],
        blank=True,
        verbose_name="Jour de réunion"
    )
    meeting_time = models.TimeField(blank=True, null=True, verbose_name="Heure de réunion")
    meeting_location = models.CharField(max_length=100, blank=True, verbose_name="Lieu de réunion")
    meeting_frequency = models.CharField(
        max_length=20,
        choices=[
            ('weekly', 'Hebdomadaire'),
            ('biweekly', 'Bihebdomadaire'),
            ('monthly', 'Mensuel'),
        ],
        blank=True,
        verbose_name="Fréquence"
    )
    
    color = models.CharField(max_length=7, default="#0d6efd", verbose_name="Couleur")
    image = models.ImageField(upload_to='groups/', blank=True, null=True, verbose_name="Image")
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Groupe"
        verbose_name_plural = "Groupes"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def member_count(self):
        return self.members.count()


class GroupMeeting(models.Model):
    """Réunion d'un groupe."""
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='meetings',
        verbose_name="Groupe"
    )
    
    date = models.DateField(verbose_name="Date")
    time = models.TimeField(blank=True, null=True, verbose_name="Heure")
    location = models.CharField(max_length=100, blank=True, verbose_name="Lieu")
    
    topic = models.CharField(max_length=200, blank=True, verbose_name="Sujet")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    attendees_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de participants")
    
    is_cancelled = models.BooleanField(default=False, verbose_name="Annulé")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Réunion"
        verbose_name_plural = "Réunions"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.group.name} - {self.date}"

