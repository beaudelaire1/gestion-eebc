"""
Modèles pour la communication et les notifications.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class EmailLog(models.Model):
    """
    Log des emails envoyés.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        SENT = 'sent', 'Envoyé'
        FAILED = 'failed', 'Échec'
        BOUNCED = 'bounced', 'Rejeté'
        OPENED = 'opened', 'Ouvert'
        CLICKED = 'clicked', 'Cliqué'
    
    recipient_email = models.EmailField(verbose_name="Email destinataire")
    recipient_name = models.CharField(max_length=200, blank=True, verbose_name="Nom destinataire")
    subject = models.CharField(max_length=200, verbose_name="Sujet")
    body = models.TextField(verbose_name="Corps du message")
    
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )
    
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Envoyé le")
    error_message = models.TextField(blank=True, verbose_name="Message d'erreur")
    
    # Tracking
    opened_at = models.DateTimeField(null=True, blank=True, verbose_name="Ouvert le")
    clicked_at = models.DateTimeField(null=True, blank=True, verbose_name="Cliqué le")
    
    # Unsubscribe token
    unsubscribe_token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        verbose_name="Token de désabonnement"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Log email"
        verbose_name_plural = "Logs emails"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient_email} - {self.subject}"
    
    @property
    def unsubscribe_url(self):
        """URL de désabonnement."""
        return f"/communication/unsubscribe/{self.unsubscribe_token}/"


class UnsubscribePreference(models.Model):
    """
    Préférences de désabonnement des utilisateurs.
    """
    
    class NotificationType(models.TextChoices):
        ALL = 'all', 'Toutes les notifications'
        EVENTS = 'events', 'Événements'
        WORSHIP = 'worship', 'Cultes'
        BIBLECLUB = 'bibleclub', 'Club Biblique'
        FINANCE = 'finance', 'Finance'
        PASTORAL = 'pastoral', 'Suivi pastoral'
        ADMINISTRATIVE = 'administrative', 'Administratif'
    
    email = models.EmailField(verbose_name="Email")
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        verbose_name="Type de notification"
    )
    
    unsubscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribe_token = models.UUIDField(verbose_name="Token utilisé")
    
    class Meta:
        verbose_name = "Préférence de désabonnement"
        verbose_name_plural = "Préférences de désabonnement"
        unique_together = ['email', 'notification_type']
        ordering = ['-unsubscribed_at']
    
    def __str__(self):
        return f"{self.email} - {self.get_notification_type_display()}"


class Announcement(models.Model):
    """
    Annonce générale.
    """
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Basse'
        NORMAL = 'normal', 'Normale'
        HIGH = 'high', 'Haute'
        URGENT = 'urgent', 'Urgente'
    
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        MEMBERS = 'members', 'Membres uniquement'
        STAFF = 'staff', 'Équipe uniquement'
    
    title = models.CharField(max_length=200, verbose_name="Titre")
    content = models.TextField(verbose_name="Contenu")
    
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
        verbose_name="Priorité"
    )
    
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        verbose_name="Visibilité"
    )
    
    # Dates
    start_date = models.DateTimeField(default=timezone.now, verbose_name="Date de début")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="Date de fin")
    
    # Notifications
    notify_by_email = models.BooleanField(default=False, verbose_name="Notifier par email")
    notify_by_sms = models.BooleanField(default=False, verbose_name="Notifier par SMS")
    
    # Métadonnées
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_announcements',
        verbose_name="Créé par"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_pinned = models.BooleanField(default=False, verbose_name="Épinglée")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Annonce"
        verbose_name_plural = "Annonces"
        ordering = ['-is_pinned', '-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def is_current(self):
        """Vérifie si l'annonce est actuellement active."""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


class Notification(models.Model):
    """
    Notification individuelle.
    """
    
    class Type(models.TextChoices):
        INFO = 'info', 'Information'
        WARNING = 'warning', 'Avertissement'
        SUCCESS = 'success', 'Succès'
        ERROR = 'error', 'Erreur'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Utilisateur",
        null=True,
        blank=True
    )
    
    title = models.CharField(max_length=200, verbose_name="Titre")
    message = models.TextField(verbose_name="Message")
    
    notification_type = models.CharField(
        max_length=10,
        choices=Type.choices,
        default=Type.INFO,
        verbose_name="Type"
    )
    
    # Lien optionnel
    action_url = models.URLField(blank=True, verbose_name="URL d'action")
    action_text = models.CharField(max_length=50, blank=True, verbose_name="Texte du lien")
    
    # Statut
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Lu le")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Marque la notification comme lue."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class EmailTemplate(models.Model):
    """
    Template d'email réutilisable.
    """
    
    class TemplateType(models.TextChoices):
        EVENT_NOTIFICATION = 'event_notification', "Notification d'événement"
        EVENT_REMINDER = 'event_reminder', "Rappel d'événement"
        EVENT_CANCELLED = 'event_cancelled', 'Événement annulé'
        TRANSPORT_CONFIRMATION = 'transport_confirmation', 'Confirmation de transport'
        WELCOME = 'welcome', 'Bienvenue'
        PASSWORD_RESET = 'password_reset', 'Réinitialisation mot de passe'
        BIRTHDAY = 'birthday', 'Anniversaire'
        DONATION_RECEIPT = 'donation_receipt', 'Reçu de don'
        CUSTOM = 'custom', 'Personnalisé'
    
    name = models.CharField(max_length=100, verbose_name="Nom du template")
    template_type = models.CharField(
        max_length=30,
        choices=TemplateType.choices,
        verbose_name="Type de template"
    )
    
    subject = models.CharField(
        max_length=200,
        verbose_name="Sujet de l'email",
        help_text="Variables disponibles: {{event.title}}, {{recipient_name}}, {{site_name}}"
    )
    
    html_content = models.TextField(
        verbose_name="Contenu HTML",
        help_text="Contenu HTML de l'email. Variables Django disponibles."
    )
    
    text_content = models.TextField(
        blank=True,
        verbose_name="Contenu texte",
        help_text="Version texte de l'email (optionnel, généré automatiquement si vide)"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    is_default = models.BooleanField(
        default=False,
        verbose_name="Template par défaut",
        help_text="Un seul template par défaut par type"
    )
    
    variables_help = models.TextField(
        blank=True,
        verbose_name="Aide sur les variables",
        help_text="Documentation des variables disponibles pour ce template"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Template d'email"
        verbose_name_plural = "Templates d'emails"
        ordering = ['template_type', 'name']
        unique_together = [('template_type', 'is_default')]
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def save(self, *args, **kwargs):
        """Assure qu'il n'y a qu'un seul template par défaut par type."""
        if self.is_default:
            # Désactiver les autres templates par défaut du même type
            EmailTemplate.objects.filter(
                template_type=self.template_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)


class SMSLog(models.Model):
    """
    Log des SMS envoyés.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        SENT = 'sent', 'Envoyé'
        FAILED = 'failed', 'Échec'
        DELIVERED = 'delivered', 'Délivré'
    
    recipient_phone = models.CharField(max_length=20, verbose_name="Téléphone destinataire")
    recipient_name = models.CharField(max_length=200, blank=True, verbose_name="Nom destinataire")
    message = models.TextField(verbose_name="Message")
    
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )
    
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Envoyé le")
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name="Délivré le")
    error_message = models.TextField(blank=True, verbose_name="Message d'erreur")
    
    # Coût (en centimes d'euro)
    cost_cents = models.PositiveIntegerField(null=True, blank=True, verbose_name="Coût (centimes)")
    
    # ID externe (Twilio, etc.)
    external_id = models.CharField(max_length=100, blank=True, verbose_name="ID externe")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Log SMS"
        verbose_name_plural = "Logs SMS"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient_phone} - {self.message[:50]}"