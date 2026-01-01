"""
Module Worship - Modèles pour la gestion liturgique.

Ce module gère :
- Les cultes et leur organisation (WorshipService)
- Les rôles assignés (ServiceRole)
- Le déroulement minute par minute (ServicePlan)

Note : Ce module exclut volontairement la gestion des chants/musique
pour se concentrer sur l'aspect administratif et organisationnel.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class WorshipService(models.Model):
    """
    Service de culte.
    
    Représente un culte dominical ou une réunion spéciale.
    Lié à un Event pour la date/heure, mais contient les
    informations liturgiques spécifiques.
    """
    
    class ServiceType(models.TextChoices):
        CULTE_DOMINICAL = 'culte_dominical', 'Culte dominical'
        CULTE_SEMAINE = 'culte_semaine', 'Culte de semaine'
        SAINTE_CENE = 'sainte_cene', 'Sainte Cène'
        BAPTEME = 'bapteme', 'Service de baptême'
        MARIAGE = 'mariage', 'Cérémonie de mariage'
        FUNERAILLES = 'funerailles', 'Service funèbre'
        SPECIAL = 'special', 'Service spécial'
    
    # Lien avec l'événement calendrier
    event = models.OneToOneField(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='worship_service',
        verbose_name="Événement"
    )
    
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        default=ServiceType.CULTE_DOMINICAL,
        verbose_name="Type de service"
    )
    
    # Thème et contenu
    theme = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Thème du culte"
    )
    
    bible_text = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Texte biblique",
        help_text="Ex: Jean 3:16-21"
    )
    
    sermon_title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Titre de la prédication"
    )
    
    sermon_notes = models.TextField(
        blank=True,
        verbose_name="Notes de prédication"
    )
    
    # Informations pratiques
    expected_attendance = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Affluence prévue"
    )
    
    actual_attendance = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Affluence réelle"
    )
    
    offering_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Total des offrandes"
    )
    
    # Statut
    is_confirmed = models.BooleanField(
        default=False,
        verbose_name="Planning confirmé"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name="Notes générales"
    )
    
    # Métadonnées
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_services',
        verbose_name="Créé par"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Service de culte"
        verbose_name_plural = "Services de culte"
        ordering = ['-event__start_date']
    
    def __str__(self):
        return f"{self.get_service_type_display()} - {self.event.start_date}"
    
    @property
    def date(self):
        return self.event.start_date
    
    @property
    def start_time(self):
        return self.event.start_time
    
    @property
    def is_complete(self):
        """Vérifie si tous les rôles essentiels sont assignés."""
        essential_roles = ['predicateur', 'dirigeant']
        assigned = self.roles.filter(
            role__in=essential_roles,
            status=ServiceRole.Status.CONFIRME
        ).values_list('role', flat=True)
        return all(role in assigned for role in essential_roles)


class ServiceRole(models.Model):
    """
    Rôle assigné pour un service de culte.
    
    Permet d'assigner des membres à des responsabilités spécifiques :
    prédicateur, dirigeant, sonorisation, accueil, offrandes, etc.
    """
    
    class RoleType(models.TextChoices):
        PREDICATEUR = 'predicateur', 'Prédicateur'
        DIRIGEANT = 'dirigeant', 'Dirigeant de culte'
        SONORISATION = 'sonorisation', 'Sonorisation'
        PROJECTION = 'projection', 'Projection'
        ACCUEIL = 'accueil', 'Accueil'
        OFFRANDES = 'offrandes', 'Gestion des offrandes'
        LECTURE = 'lecture', 'Lecture biblique'
        PRIERE = 'priere', 'Prière'
        ANNONCES = 'annonces', 'Annonces'
        SAINTE_CENE = 'sainte_cene', 'Service Sainte Cène'
        ENFANTS = 'enfants', 'Responsable enfants'
        STREAMING = 'streaming', 'Streaming/Enregistrement'
        AUTRE = 'autre', 'Autre'
    
    class Status(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        CONFIRME = 'confirme', 'Confirmé'
        DECLINE = 'decline', 'Décliné'
        REMPLACE = 'remplace', 'Remplacé'
    
    service = models.ForeignKey(
        WorshipService,
        on_delete=models.CASCADE,
        related_name='roles',
        verbose_name="Service"
    )
    
    role = models.CharField(
        max_length=20,
        choices=RoleType.choices,
        verbose_name="Rôle"
    )
    
    # Personne assignée
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_roles',
        verbose_name="Membre assigné"
    )
    
    # Alternative : utilisateur sans profil membre
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_roles',
        verbose_name="Utilisateur assigné"
    )
    
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.EN_ATTENTE,
        verbose_name="Statut"
    )
    
    # Remplacement
    replaced_by = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replacement_roles',
        verbose_name="Remplacé par"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    # Notification
    notified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Notifié le"
    )
    
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Confirmé le"
    )
    
    class Meta:
        verbose_name = "Rôle de service"
        verbose_name_plural = "Rôles de service"
        ordering = ['service', 'role']
        # Un seul rôle par type par service (sauf exceptions)
        unique_together = ['service', 'role', 'member']
    
    def __str__(self):
        assignee = self.member or self.user or "Non assigné"
        return f"{self.get_role_display()} - {assignee}"
    
    @property
    def assignee_name(self):
        """Retourne le nom de la personne assignée."""
        if self.member:
            return self.member.full_name
        if self.user:
            return self.user.get_full_name() or self.user.username
        return "Non assigné"
    
    def confirm(self):
        """Confirme l'assignation."""
        from django.utils import timezone
        self.status = self.Status.CONFIRME
        self.confirmed_at = timezone.now()
        self.save()
    
    def decline(self):
        """Décline l'assignation."""
        self.status = self.Status.DECLINE
        self.save()


class ServicePlanItem(models.Model):
    """
    Élément du déroulement d'un service.
    
    Représente un segment du culte avec son heure de début et sa durée.
    Permet de créer une "Run Sheet" minute par minute.
    """
    
    class ItemType(models.TextChoices):
        ACCUEIL = 'accueil', 'Accueil'
        LOUANGE = 'louange', 'Temps de louange'
        PRIERE = 'priere', 'Prière'
        LECTURE = 'lecture', 'Lecture biblique'
        ANNONCES = 'annonces', 'Annonces'
        OFFRANDE = 'offrande', 'Offrande'
        PREDICATION = 'predication', 'Prédication'
        APPEL = 'appel', 'Appel'
        SAINTE_CENE = 'sainte_cene', 'Sainte Cène'
        BAPTEME = 'bapteme', 'Baptême'
        TEMOIGNAGE = 'temoignage', 'Témoignage'
        VIDEO = 'video', 'Vidéo/Présentation'
        BENEDICTION = 'benediction', 'Bénédiction'
        PAUSE = 'pause', 'Pause/Transition'
        AUTRE = 'autre', 'Autre'
    
    service = models.ForeignKey(
        WorshipService,
        on_delete=models.CASCADE,
        related_name='plan_items',
        verbose_name="Service"
    )
    
    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
        verbose_name="Type"
    )
    
    title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Titre/Description"
    )
    
    # Timing
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Ordre"
    )
    
    start_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Heure de début"
    )
    
    duration_minutes = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        verbose_name="Durée (minutes)"
    )
    
    # Responsable
    responsible = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plan_responsibilities',
        verbose_name="Responsable"
    )
    
    # Notes techniques
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Instructions pour l'équipe technique"
    )
    
    # Ressources
    resources_needed = models.TextField(
        blank=True,
        verbose_name="Ressources nécessaires",
        help_text="Micro, pupitre, écran, etc."
    )
    
    class Meta:
        verbose_name = "Élément de programme"
        verbose_name_plural = "Éléments de programme"
        ordering = ['service', 'order', 'start_time']
    
    def __str__(self):
        time_str = self.start_time.strftime('%H:%M') if self.start_time else f"#{self.order}"
        return f"{time_str} - {self.get_item_type_display()}"
    
    @property
    def end_time(self):
        """Calcule l'heure de fin estimée."""
        if self.start_time:
            from datetime import datetime, timedelta
            start = datetime.combine(datetime.today(), self.start_time)
            end = start + timedelta(minutes=self.duration_minutes)
            return end.time()
        return None


class ServiceTemplate(models.Model):
    """
    Modèle de service réutilisable.
    
    Permet de créer des templates de déroulement standard
    (ex: "Culte dominical standard", "Service de baptême")
    pour accélérer la planification.
    """
    
    name = models.CharField(max_length=100, verbose_name="Nom du modèle")
    description = models.TextField(blank=True, verbose_name="Description")
    
    service_type = models.CharField(
        max_length=20,
        choices=WorshipService.ServiceType.choices,
        default=WorshipService.ServiceType.CULTE_DOMINICAL,
        verbose_name="Type de service"
    )
    
    # Durée totale estimée
    estimated_duration = models.PositiveIntegerField(
        default=90,
        verbose_name="Durée estimée (minutes)"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Modèle de service"
        verbose_name_plural = "Modèles de service"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ServiceTemplateItem(models.Model):
    """Élément d'un modèle de service."""
    
    template = models.ForeignKey(
        ServiceTemplate,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Modèle"
    )
    
    item_type = models.CharField(
        max_length=20,
        choices=ServicePlanItem.ItemType.choices,
        verbose_name="Type"
    )
    
    title = models.CharField(max_length=200, blank=True, verbose_name="Titre")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    duration_minutes = models.PositiveIntegerField(default=5, verbose_name="Durée (minutes)")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Élément de modèle"
        verbose_name_plural = "Éléments de modèle"
        ordering = ['template', 'order']
    
    def __str__(self):
        return f"{self.template.name} - {self.get_item_type_display()}"
