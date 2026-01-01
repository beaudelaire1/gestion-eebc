from django.db import models
from django.conf import settings


class EventCategory(models.Model):
    """Catégorie d'événement."""
    name = models.CharField(max_length=100, verbose_name="Nom")
    color = models.CharField(max_length=7, default="#0d6efd", verbose_name="Couleur")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Icône")
    
    class Meta:
        verbose_name = "Catégorie d'événement"
        verbose_name_plural = "Catégories d'événements"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Event(models.Model):
    """
    Modèle représentant un événement de l'église.
    """
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        MEMBERS = 'members', 'Membres uniquement'
        PRIVATE = 'private', 'Privé'
    
    class RecurrenceType(models.TextChoices):
        NONE = 'none', 'Aucune'
        DAILY = 'daily', 'Quotidien'
        WEEKLY = 'weekly', 'Hebdomadaire'
        BIWEEKLY = 'biweekly', 'Bihebdomadaire'
        MONTHLY = 'monthly', 'Mensuel'
        TRIMESTERLY = 'trimesterly', 'Trimestriel'
        YEARLY = 'yearly', 'Annuel'
    
    class NotificationScope(models.TextChoices):
        NONE = 'none', 'Aucune notification'
        ORGANIZER = 'organizer', 'Organisateur uniquement'
        GROUP = 'group', 'Groupe concerné'
        DEPARTMENT = 'department', 'Département concerné'
        MEMBERS = 'members', 'Tous les membres'
        ALL = 'all', 'Tout le monde'
    
    title = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")
    
    category = models.ForeignKey(
        EventCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        verbose_name="Catégorie"
    )
    
    # Date et heure
    start_date = models.DateField(verbose_name="Date de début")
    start_time = models.TimeField(blank=True, null=True, verbose_name="Heure de début")
    end_date = models.DateField(blank=True, null=True, verbose_name="Date de fin")
    end_time = models.TimeField(blank=True, null=True, verbose_name="Heure de fin")
    all_day = models.BooleanField(default=False, verbose_name="Toute la journée")
    
    # Lieu
    location = models.CharField(max_length=200, blank=True, verbose_name="Lieu")
    address = models.TextField(blank=True, verbose_name="Adresse")
    
    # Récurrence
    recurrence = models.CharField(
        max_length=15,
        choices=RecurrenceType.choices,
        default=RecurrenceType.NONE,
        verbose_name="Récurrence"
    )
    recurrence_end_date = models.DateField(blank=True, null=True, verbose_name="Fin de récurrence")
    
    # Visibilité
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        verbose_name="Visibilité"
    )
    
    # Portée des notifications
    notification_scope = models.CharField(
        max_length=15,
        choices=NotificationScope.choices,
        default=NotificationScope.NONE,
        verbose_name="Portée des notifications",
        help_text="Qui doit recevoir les notifications pour cet événement"
    )
    
    # Responsable
    organizers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name='organized_events',
        verbose_name="Organisateur"
    )
    
    # Département/Groupe lié
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        verbose_name="Département"
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        verbose_name="Groupe"
    )
    
    # Notifications
    notify_before = models.PositiveIntegerField(
        default=1,
        verbose_name="Notification (jours avant)",
        help_text="Nombre de jours avant l'événement pour envoyer une notification"
    )
    notification_sent = models.BooleanField(default=False, verbose_name="Notification envoyée")
    
    is_cancelled = models.BooleanField(default=False, verbose_name="Annulé")
    
    image = models.ImageField(upload_to='events/', blank=True, null=True, verbose_name="Image")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ['start_date', 'start_time']
    
    def __str__(self):
        return f"{self.title} - {self.start_date}"
    
    @property
    def color(self):
        """Couleur de l'événement (basée sur la catégorie)."""
        if self.category:
            return self.category.color
        return "#0d6efd"
    
    @property
    def icon(self):
        """Icône de l'événement (basée sur la catégorie)."""
        if self.category and self.category.icon:
            return self.category.icon
        return "bi-calendar-event"
    
    @property
    def is_upcoming(self):
        from datetime import date
        return self.start_date >= date.today() and not self.is_cancelled
    
    @property
    def is_today(self):
        from datetime import date
        return self.start_date == date.today()
    
    def get_notification_recipients(self):
        """Retourne la liste des emails à notifier selon la portée."""
        from apps.members.models import Member
        from apps.accounts.models import User
        
        emails = set()
        
        if self.notification_scope == self.NotificationScope.NONE:
            return []
        
        if self.notification_scope == self.NotificationScope.ORGANIZER:
            # ManyToMany - récupérer tous les organisateurs
            for organizer in self.organizers.all():
                if organizer.email:
                    emails.add(organizer.email)
        
        elif self.notification_scope == self.NotificationScope.GROUP:
            if self.group:
                for member in self.group.members.all():
                    if member.email:
                        emails.add(member.email)
        
        elif self.notification_scope == self.NotificationScope.DEPARTMENT:
            if self.department:
                for member in self.department.members.all():
                    if member.email:
                        emails.add(member.email)
                if self.department.leader and self.department.leader.email:
                    emails.add(self.department.leader.email)
        
        elif self.notification_scope == self.NotificationScope.MEMBERS:
            for member in Member.objects.filter(status='actif'):
                if member.email:
                    emails.add(member.email)
        
        elif self.notification_scope == self.NotificationScope.ALL:
            for user in User.objects.filter(is_active=True):
                if user.email:
                    emails.add(user.email)
            for member in Member.objects.all():
                if member.email:
                    emails.add(member.email)
        
        return list(emails)


class EventRegistration(models.Model):
    """Inscription à un événement."""
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='registrations',
        verbose_name="Événement"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_registrations',
        verbose_name="Participant"
    )
    
    registered_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        unique_together = ['event', 'user']
    
    def __str__(self):
        return f"{self.user} - {self.event}"
