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
# crete member id format : EEBC-M-first occurence name and first name and random number
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


# =============================================================================
# MODULE PASTORAL CRM - Suivi des âmes
# =============================================================================

class LifeEvent(models.Model):
    """
    Événement de vie d'un membre.
    
    Permet de tracer les moments importants : naissance, décès, mariage,
    baptême, hospitalisation, etc. Ces événements déclenchent des alertes
    et des actions pastorales.
    """
    
    class EventType(models.TextChoices):
        NAISSANCE = 'naissance', 'Naissance'
        DECES = 'deces', 'Décès'
        MARIAGE = 'mariage', 'Mariage'
        BAPTEME = 'bapteme', 'Baptême'
        HOSPITALISATION = 'hospitalisation', 'Hospitalisation'
        DEUIL = 'deuil', 'Deuil (proche)'
        CONVERSION = 'conversion', 'Conversion'
        ANNIVERSAIRE_MARIAGE = 'anniversaire_mariage', 'Anniversaire de mariage'
        AUTRE = 'autre', 'Autre'
    
    class Priority(models.TextChoices):
        HAUTE = 'haute', 'Haute'
        NORMALE = 'normale', 'Normale'
        BASSE = 'basse', 'Basse'
    
    event_type = models.CharField(
        max_length=25,
        choices=EventType.choices,
        verbose_name="Type d'événement"
    )
    
    event_date = models.DateField(verbose_name="Date de l'événement")
    
    # Membre(s) concerné(s)
    primary_member = models.ForeignKey(
        'Member',
        on_delete=models.CASCADE,
        related_name='life_events',
        verbose_name="Membre principal"
    )
    
    related_members = models.ManyToManyField(
        'Member',
        blank=True,
        related_name='related_life_events',
        verbose_name="Membres liés",
        help_text="Autres membres concernés (conjoint, famille...)"
    )
    
    # Détails
    title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Titre",
        help_text="Ex: 'Naissance de Paul', 'Mariage Jean & Marie'"
    )
    
    description = models.TextField(blank=True, verbose_name="Description")
    
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMALE,
        verbose_name="Priorité"
    )
    
    # Suivi pastoral
    requires_visit = models.BooleanField(
        default=True,
        verbose_name="Visite requise",
        help_text="Cocher si une visite pastorale est nécessaire"
    )
    
    visit_completed = models.BooleanField(
        default=False,
        verbose_name="Visite effectuée"
    )
    
    announce_sunday = models.BooleanField(
        default=False,
        verbose_name="Annoncer dimanche",
        help_text="À annoncer lors du culte"
    )
    
    announced = models.BooleanField(
        default=False,
        verbose_name="Annoncé"
    )
    
    # Métadonnées
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_life_events',
        verbose_name="Enregistré par"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes pastorales")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Événement de vie"
        verbose_name_plural = "Événements de vie"
        ordering = ['-event_date', '-created_at']
    
    def __str__(self):
        if self.title:
            return self.title
        return f"{self.get_event_type_display()} - {self.primary_member}"
    
    def save(self, *args, **kwargs):
        """Génère un titre automatique si absent."""
        if not self.title:
            self.title = f"{self.get_event_type_display()} - {self.primary_member.full_name}"
        super().save(*args, **kwargs)


class VisitationLog(models.Model):
    """
    Journal des visites pastorales.
    
    Permet de suivre qui a été visité, quand, et par qui.
    Essentiel pour le suivi pastoral et la "mémoire" de l'église.
    """
    
    class VisitType(models.TextChoices):
        DOMICILE = 'domicile', 'Visite à domicile'
        HOPITAL = 'hopital', 'Visite à l\'hôpital'
        ZOOM = 'zoom', 'Appel vidéo (Zoom/WhatsApp)'
        TELEPHONE = 'telephone', 'Appel téléphonique'
        BUREAU = 'bureau', 'Rencontre au bureau'
        AUTRE = 'autre', 'Autre'
    
    class Status(models.TextChoices):
        PLANIFIE = 'planifie', 'Planifié'
        A_FAIRE = 'a_faire', 'À faire'
        EFFECTUE = 'effectue', 'Effectué'
        ANNULE = 'annule', 'Annulé'
        REPORTE = 'reporte', 'Reporté'
    
    # Qui visite qui
    visitor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='visits_made',
        verbose_name="Visiteur"
    )
    
    member = models.ForeignKey(
        'Member',
        on_delete=models.CASCADE,
        related_name='visits_received',
        verbose_name="Membre visité"
    )
    
    # Détails de la visite
    visit_type = models.CharField(
        max_length=15,
        choices=VisitType.choices,
        default=VisitType.DOMICILE,
        verbose_name="Type de visite"
    )
    
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PLANIFIE,
        verbose_name="Statut"
    )
    
    # Dates
    scheduled_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date prévue"
    )
    
    visit_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date effective"
    )
    
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Durée (minutes)"
    )
    
    # Lien avec un événement de vie
    life_event = models.ForeignKey(
        LifeEvent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visits',
        verbose_name="Événement lié"
    )
    
    # Compte-rendu
    summary = models.TextField(
        blank=True,
        verbose_name="Résumé de la visite"
    )
    
    prayer_requests = models.TextField(
        blank=True,
        verbose_name="Sujets de prière"
    )
    
    follow_up_needed = models.BooleanField(
        default=False,
        verbose_name="Suivi nécessaire"
    )
    
    follow_up_notes = models.TextField(
        blank=True,
        verbose_name="Notes de suivi"
    )
    
    # Confidentialité
    is_confidential = models.BooleanField(
        default=False,
        verbose_name="Confidentiel",
        help_text="Visible uniquement par le pasteur principal"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Visite pastorale"
        verbose_name_plural = "Visites pastorales"
        ordering = ['-visit_date', '-scheduled_date']
    
    def __str__(self):
        date_str = self.visit_date or self.scheduled_date or "Non planifié"
        return f"{self.member} - {date_str} ({self.get_status_display()})"


# Extension du modèle Member avec des propriétés calculées
def _get_last_visit_date(self):
    """Retourne la date de la dernière visite effectuée."""
    last_visit = self.visits_received.filter(
        status=VisitationLog.Status.EFFECTUE
    ).order_by('-visit_date').first()
    return last_visit.visit_date if last_visit else None

def _get_days_since_last_visit(self):
    """Retourne le nombre de jours depuis la dernière visite."""
    from datetime import date
    last_date = self.last_visit_date
    if last_date:
        return (date.today() - last_date).days
    return None

def _needs_visit(self):
    """Retourne True si le membre n'a pas été visité depuis 6 mois."""
    days = self.days_since_last_visit
    if days is None:
        return True  # Jamais visité
    return days > 180  # 6 mois

def _get_recent_life_events(self):
    """Retourne les événements de vie des 12 derniers mois."""
    from datetime import date, timedelta
    one_year_ago = date.today() - timedelta(days=365)
    return self.life_events.filter(event_date__gte=one_year_ago)

# Ajout des propriétés au modèle Member
Member.last_visit_date = property(_get_last_visit_date)
Member.days_since_last_visit = property(_get_days_since_last_visit)
Member.needs_visit = property(_needs_visit)
Member.recent_life_events = property(_get_recent_life_events)
