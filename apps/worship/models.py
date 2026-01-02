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
        CHORISTE = 'choriste', 'Choriste'
        MUSICIEN = 'musicien', 'Musicien'
        CHEF_CHORALE = 'chef_chorale', 'Chef de chorale'
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


# =============================================================================
# PLANIFICATION MENSUELLE DES CULTES
# =============================================================================

class MonthlySchedule(models.Model):
    """
    Planification mensuelle des cultes.
    
    Permet de préparer un mois complet de cultes (4-5 dimanches)
    et de gérer les notifications automatiques.
    """
    
    class Status(models.TextChoices):
        BROUILLON = 'brouillon', 'Brouillon'
        EN_COURS = 'en_cours', 'En cours de validation'
        VALIDE = 'valide', 'Validé'
        PUBLIE = 'publie', 'Publié'
    
    # Période
    year = models.PositiveIntegerField(verbose_name="Année")
    month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Mois"
    )
    
    # Site
    site = models.ForeignKey(
        'core.Site',
        on_delete=models.CASCADE,
        related_name='monthly_schedules',
        verbose_name="Site"
    )
    
    # Statut
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.BROUILLON,
        verbose_name="Statut"
    )
    
    # Notifications
    notification_day = models.PositiveIntegerField(
        default=3,  # Mercredi par défaut (0=Lundi, 6=Dimanche)
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        verbose_name="Jour de notification",
        help_text="0=Lundi, 1=Mardi, 2=Mercredi, 3=Jeudi, 4=Vendredi, 5=Samedi, 6=Dimanche"
    )
    
    days_before_service = models.PositiveIntegerField(
        default=4,
        verbose_name="Jours avant le culte",
        help_text="Nombre de jours avant le culte pour envoyer la notification"
    )
    
    notify_by_email = models.BooleanField(default=True, verbose_name="Notifier par email")
    notify_by_sms = models.BooleanField(default=False, verbose_name="Notifier par SMS")
    notify_by_whatsapp = models.BooleanField(default=False, verbose_name="Notifier par WhatsApp")
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    # Métadonnées
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_schedules',
        verbose_name="Créé par"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="Publié le")
    
    class Meta:
        verbose_name = "Planning mensuel"
        verbose_name_plural = "Plannings mensuels"
        ordering = ['-year', '-month']
        unique_together = ['year', 'month', 'site']
    
    def __str__(self):
        months = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        return f"{months[self.month]} {self.year} - {self.site.name}"
    
    @property
    def month_name(self):
        months = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        return months[self.month]
    
    def get_sundays(self):
        """Retourne tous les dimanches du mois."""
        import calendar
        from datetime import date
        
        cal = calendar.Calendar()
        sundays = []
        for day in cal.itermonthdates(self.year, self.month):
            if day.month == self.month and day.weekday() == 6:  # Dimanche
                sundays.append(day)
        return sundays
    
    def publish(self):
        """Publie le planning et programme les notifications."""
        from django.utils import timezone
        self.status = self.Status.PUBLIE
        self.published_at = timezone.now()
        self.save()
        
        # Programmer les notifications pour chaque culte
        for service in self.services.all():
            service.schedule_notifications()


class ScheduledService(models.Model):
    """
    Culte programmé dans un planning mensuel.
    
    Représente un dimanche spécifique avec tous les rôles assignés.
    """
    
    schedule = models.ForeignKey(
        MonthlySchedule,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name="Planning"
    )
    
    # Date du culte
    date = models.DateField(verbose_name="Date")
    start_time = models.TimeField(default='09:30', verbose_name="Heure de début")
    
    # Thème
    theme = models.CharField(max_length=200, blank=True, verbose_name="Thème")
    bible_text = models.CharField(max_length=200, blank=True, verbose_name="Texte biblique")
    
    # Rôles principaux (accès rapide)
    preacher = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='preaching_services',
        verbose_name="Prédicateur"
    )
    
    worship_leader = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='led_services',
        verbose_name="Dirigeant"
    )
    
    choir_leader = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='choir_led_services',
        verbose_name="Chef de chorale"
    )
    
    # Équipes (plusieurs personnes)
    singers = models.ManyToManyField(
        'members.Member',
        blank=True,
        related_name='singing_services',
        verbose_name="Choristes"
    )
    
    musicians = models.ManyToManyField(
        'members.Member',
        blank=True,
        related_name='musician_services',
        verbose_name="Musiciens"
    )
    
    # Autres rôles
    sound_tech = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sound_services',
        verbose_name="Sonorisation"
    )
    
    projection = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='projection_services',
        verbose_name="Projection"
    )
    
    # Statut des notifications
    notifications_sent = models.BooleanField(default=False, verbose_name="Notifications envoyées")
    notifications_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Culte programmé"
        verbose_name_plural = "Cultes programmés"
        ordering = ['date']
        unique_together = ['schedule', 'date']
    
    def __str__(self):
        return f"Culte du {self.date.strftime('%d/%m/%Y')}"
    
    def get_all_participants(self):
        """Retourne tous les participants avec leurs rôles."""
        participants = []
        
        if self.preacher:
            participants.append({'member': self.preacher, 'role': 'Prédicateur'})
        if self.worship_leader:
            participants.append({'member': self.worship_leader, 'role': 'Dirigeant'})
        if self.choir_leader:
            participants.append({'member': self.choir_leader, 'role': 'Chef de chorale'})
        if self.sound_tech:
            participants.append({'member': self.sound_tech, 'role': 'Sonorisation'})
        if self.projection:
            participants.append({'member': self.projection, 'role': 'Projection'})
        
        for singer in self.singers.all():
            participants.append({'member': singer, 'role': 'Choriste'})
        
        for musician in self.musicians.all():
            participants.append({'member': musician, 'role': 'Musicien'})
        
        return participants
    
    def schedule_notifications(self):
        """Programme l'envoi des notifications."""
        from datetime import timedelta
        from django.utils import timezone
        
        # Calculer la date d'envoi
        send_date = self.date - timedelta(days=self.schedule.days_before_service)
        
        # Créer une tâche de notification
        ServiceNotification.objects.update_or_create(
            scheduled_service=self,
            defaults={
                'scheduled_date': send_date,
                'notify_email': self.schedule.notify_by_email,
                'notify_sms': self.schedule.notify_by_sms,
                'notify_whatsapp': self.schedule.notify_by_whatsapp,
            }
        )
    
    def send_notifications(self):
        """Envoie les notifications à tous les participants."""
        from django.utils import timezone
        from apps.communication.notification_service import NotificationService
        
        participants = self.get_all_participants()
        notification_service = NotificationService()
        
        for p in participants:
            member = p['member']
            role = p['role']
            
            message = f"""Bonjour {member.first_name},

Vous êtes programmé(e) pour le culte du {self.date.strftime('%d/%m/%Y')} à {self.start_time.strftime('%H:%M')}.

Votre rôle : {role}
{f"Thème : {self.theme}" if self.theme else ""}
{f"Texte : {self.bible_text}" if self.bible_text else ""}

Merci de confirmer votre disponibilité.

Fraternellement,
{self.schedule.site.name}"""
            
            # Email
            if self.schedule.notify_by_email and member.email:
                notification_service.send_email(
                    to_email=member.email,
                    subject=f"Programme culte du {self.date.strftime('%d/%m/%Y')} - {role}",
                    message=message
                )
            
            # SMS
            if self.schedule.notify_by_sms and member.phone:
                short_msg = f"Culte {self.date.strftime('%d/%m')}: vous êtes {role}. Confirmez SVP."
                notification_service.send_sms(member.phone, short_msg)
            
            # WhatsApp
            if self.schedule.notify_by_whatsapp and member.whatsapp_number:
                notification_service.send_whatsapp(member.whatsapp_number, message)
        
        self.notifications_sent = True
        self.notifications_sent_at = timezone.now()
        self.save()


class ServiceNotification(models.Model):
    """
    Notification programmée pour un culte.
    
    Gère l'envoi automatique des rappels aux participants.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        SENT = 'sent', 'Envoyé'
        FAILED = 'failed', 'Échec'
        CANCELLED = 'cancelled', 'Annulé'
    
    scheduled_service = models.OneToOneField(
        ScheduledService,
        on_delete=models.CASCADE,
        related_name='notification',
        verbose_name="Culte"
    )
    
    scheduled_date = models.DateField(verbose_name="Date d'envoi prévue")
    
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)
    notify_whatsapp = models.BooleanField(default=False)
    
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )
    
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Notification de culte"
        verbose_name_plural = "Notifications de culte"
        ordering = ['scheduled_date']
    
    def __str__(self):
        return f"Notification pour {self.scheduled_service}"
    
    def send(self):
        """Envoie la notification."""
        from django.utils import timezone
        
        try:
            self.scheduled_service.send_notifications()
            self.status = self.Status.SENT
            self.sent_at = timezone.now()
        except Exception as e:
            self.status = self.Status.FAILED
            self.error_message = str(e)
        
        self.save()


# =============================================================================
# TOKENS DE CONFIRMATION DES RÔLES
# =============================================================================

import uuid
from datetime import timedelta


class RoleAssignment(models.Model):
    """
    Assignation d'un rôle avec token de confirmation.
    
    Chaque assignation génère un token unique permettant au membre
    de confirmer ou refuser sa participation via un lien (sans connexion).
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        ACCEPTED = 'accepted', 'Accepté'
        DECLINED = 'declined', 'Refusé'
        EXPIRED = 'expired', 'Expiré'
    
    class RoleType(models.TextChoices):
        PREACHER = 'preacher', 'Prédicateur'
        WORSHIP_LEADER = 'worship_leader', 'Dirigeant de culte'
        CHOIR_LEADER = 'choir_leader', 'Chef de chorale'
        SINGER = 'singer', 'Choriste'
        MUSICIAN = 'musician', 'Musicien'
        SOUND_TECH = 'sound_tech', 'Sonorisation'
        PROJECTION = 'projection', 'Projection'
    
    # Lien avec le culte
    scheduled_service = models.ForeignKey(
        ScheduledService,
        on_delete=models.CASCADE,
        related_name='role_assignments',
        verbose_name="Culte"
    )
    
    # Membre assigné
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='role_assignments',
        verbose_name="Membre"
    )
    
    # Type de rôle
    role = models.CharField(
        max_length=20,
        choices=RoleType.choices,
        verbose_name="Rôle"
    )
    
    # Token unique pour confirmation
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Token"
    )
    
    # Statut
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True, verbose_name="Notifié le")
    responded_at = models.DateTimeField(null=True, blank=True, verbose_name="Répondu le")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Expire le")
    
    # Raison du refus (optionnel)
    decline_reason = models.TextField(blank=True, verbose_name="Raison du refus")
    
    # Remplacement suggéré
    suggested_replacement = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='suggested_as_replacement',
        verbose_name="Remplacement suggéré"
    )
    
    class Meta:
        verbose_name = "Assignation de rôle"
        verbose_name_plural = "Assignations de rôles"
        ordering = ['scheduled_service__date', 'role']
        unique_together = ['scheduled_service', 'member', 'role']
    
    def __str__(self):
        return f"{self.member.full_name} - {self.get_role_display()} ({self.scheduled_service.date})"
    
    def save(self, *args, **kwargs):
        # Définir la date d'expiration (48h avant le culte)
        if not self.expires_at and self.scheduled_service:
            from django.utils import timezone
            from datetime import datetime
            service_datetime = datetime.combine(
                self.scheduled_service.date,
                self.scheduled_service.start_time
            )
            self.expires_at = timezone.make_aware(service_datetime) - timedelta(hours=48)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Vérifie si le token est expiré."""
        from django.utils import timezone
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    @property
    def confirmation_url(self):
        """URL de confirmation."""
        return f"/worship/confirm/{self.token}/"
    
    @property
    def decline_url(self):
        """URL de refus."""
        return f"/worship/decline/{self.token}/"
    
    def accept(self):
        """Accepte l'assignation."""
        from django.utils import timezone
        
        if self.is_expired:
            self.status = self.Status.EXPIRED
        else:
            self.status = self.Status.ACCEPTED
        
        self.responded_at = timezone.now()
        self.save()
        
        # Mettre à jour le ScheduledService
        self._update_service_assignment()
    
    def decline(self, reason='', suggested_replacement=None):
        """Refuse l'assignation."""
        from django.utils import timezone
        
        self.status = self.Status.DECLINED
        self.responded_at = timezone.now()
        self.decline_reason = reason
        self.suggested_replacement = suggested_replacement
        self.save()
        
        # Retirer du ScheduledService
        self._remove_service_assignment()
    
    def _update_service_assignment(self):
        """Met à jour l'assignation dans ScheduledService."""
        service = self.scheduled_service
        
        if self.role == self.RoleType.PREACHER:
            service.preacher = self.member
        elif self.role == self.RoleType.WORSHIP_LEADER:
            service.worship_leader = self.member
        elif self.role == self.RoleType.CHOIR_LEADER:
            service.choir_leader = self.member
        elif self.role == self.RoleType.SOUND_TECH:
            service.sound_tech = self.member
        elif self.role == self.RoleType.PROJECTION:
            service.projection = self.member
        elif self.role == self.RoleType.SINGER:
            service.singers.add(self.member)
        elif self.role == self.RoleType.MUSICIAN:
            service.musicians.add(self.member)
        
        service.save()
    
    def _remove_service_assignment(self):
        """Retire l'assignation du ScheduledService."""
        service = self.scheduled_service
        
        if self.role == self.RoleType.PREACHER and service.preacher == self.member:
            service.preacher = None
        elif self.role == self.RoleType.WORSHIP_LEADER and service.worship_leader == self.member:
            service.worship_leader = None
        elif self.role == self.RoleType.CHOIR_LEADER and service.choir_leader == self.member:
            service.choir_leader = None
        elif self.role == self.RoleType.SOUND_TECH and service.sound_tech == self.member:
            service.sound_tech = None
        elif self.role == self.RoleType.PROJECTION and service.projection == self.member:
            service.projection = None
        elif self.role == self.RoleType.SINGER:
            service.singers.remove(self.member)
        elif self.role == self.RoleType.MUSICIAN:
            service.musicians.remove(self.member)
        
        service.save()
    
    def send_notification(self, base_url=''):
        """Envoie la notification avec les liens de confirmation."""
        from django.utils import timezone
        from apps.communication.notification_service import NotificationService
        
        schedule = self.scheduled_service.schedule
        service = self.scheduled_service
        
        confirm_url = f"{base_url}/worship/confirm/{self.token}/"
        decline_url = f"{base_url}/worship/decline/{self.token}/"
        
        message = f"""Bonjour {self.member.first_name},

Vous êtes sollicité(e) pour le culte du {service.date.strftime('%d/%m/%Y')} à {service.start_time.strftime('%H:%M')}.

📋 Rôle proposé : {self.get_role_display()}
📍 Lieu : {schedule.site.name}
{f"🎯 Thème : {service.theme}" if service.theme else ""}

Merci de confirmer votre disponibilité :

✅ ACCEPTER : {confirm_url}
❌ REFUSER : {decline_url}

⏰ Merci de répondre avant le {self.expires_at.strftime('%d/%m/%Y à %H:%M') if self.expires_at else 'plus tôt possible'}.

Fraternellement,
{schedule.site.name}"""
        
        notification_service = NotificationService()
        
        # Email
        if schedule.notify_by_email and self.member.email:
            notification_service.send_email(
                to_email=self.member.email,
                subject=f"🙏 Confirmation requise - {self.get_role_display()} du {service.date.strftime('%d/%m')}",
                message=message,
                html_message=self._get_html_notification(confirm_url, decline_url)
            )
        
        # SMS
        if schedule.notify_by_sms and self.member.phone:
            sms_msg = f"Culte {service.date.strftime('%d/%m')}: {self.get_role_display()}. Confirmez: {confirm_url}"
            notification_service.send_sms(self.member.phone, sms_msg)
        
        # WhatsApp
        if schedule.notify_by_whatsapp and self.member.whatsapp_number:
            notification_service.send_whatsapp(self.member.whatsapp_number, message)
        
        self.notified_at = timezone.now()
        self.save(update_fields=['notified_at'])
    
    def _get_html_notification(self, confirm_url, decline_url):
        """Génère le HTML de la notification."""
        service = self.scheduled_service
        schedule = service.schedule
        
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #0A36FF 0%, #1e3a5f 100%); color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">Confirmation requise</h1>
            </div>
            
            <div style="padding: 30px; background: #f8f9fa;">
                <p>Bonjour <strong>{self.member.first_name}</strong>,</p>
                
                <p>Vous êtes sollicité(e) pour participer au culte :</p>
                
                <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>📅 Date :</strong> {service.date.strftime('%A %d %B %Y')}</p>
                    <p style="margin: 5px 0;"><strong>⏰ Heure :</strong> {service.start_time.strftime('%H:%M')}</p>
                    <p style="margin: 5px 0;"><strong>📍 Lieu :</strong> {schedule.site.name}</p>
                    <p style="margin: 5px 0;"><strong>🎯 Rôle :</strong> <span style="color: #0A36FF; font-weight: bold;">{self.get_role_display()}</span></p>
                    {f'<p style="margin: 5px 0;"><strong>📖 Thème :</strong> {service.theme}</p>' if service.theme else ''}
                </div>
                
                <p>Merci de confirmer votre disponibilité :</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{confirm_url}" style="background: #28a745; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; margin: 10px; display: inline-block; font-weight: bold;">
                        ✅ J'ACCEPTE
                    </a>
                    <a href="{decline_url}" style="background: #dc3545; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; margin: 10px; display: inline-block; font-weight: bold;">
                        ❌ JE REFUSE
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    ⏰ Merci de répondre avant le <strong>{self.expires_at.strftime('%d/%m/%Y à %H:%M') if self.expires_at else 'plus tôt possible'}</strong>.
                </p>
            </div>
            
            <div style="background: #1e3a5f; color: white; padding: 15px; text-align: center; font-size: 12px;">
                {schedule.site.name}
            </div>
        </div>
        """
