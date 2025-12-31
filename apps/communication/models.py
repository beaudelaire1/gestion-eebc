from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Notification interne pour les utilisateurs.
    """
    class NotificationType(models.TextChoices):
        INFO = 'info', 'Information'
        WARNING = 'warning', 'Avertissement'
        SUCCESS = 'success', 'Succès'
        ERROR = 'error', 'Erreur'
        EVENT = 'event', 'Événement'
        ABSENCE = 'absence', 'Absence'
        CAMPAIGN = 'campaign', 'Campagne'
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Destinataire"
    )
    
    title = models.CharField(max_length=200, verbose_name="Titre")
    message = models.TextField(verbose_name="Message")
    
    notification_type = models.CharField(
        max_length=15,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
        verbose_name="Type"
    )
    
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    
    # Lien optionnel vers un objet
    link = models.CharField(max_length=500, blank=True, verbose_name="Lien")
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True, verbose_name="Lu le")
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.recipient}"
    
    def mark_as_read(self):
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class EmailLog(models.Model):
    """
    Log des emails envoyés.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        SENT = 'sent', 'Envoyé'
        FAILED = 'failed', 'Échec'
    
    recipient_email = models.EmailField(verbose_name="Email destinataire")
    recipient_name = models.CharField(max_length=200, blank=True, verbose_name="Nom destinataire")
    
    subject = models.CharField(max_length=200, verbose_name="Sujet")
    body = models.TextField(verbose_name="Corps du message")
    
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )
    
    error_message = models.TextField(blank=True, verbose_name="Message d'erreur")
    
    sent_at = models.DateTimeField(blank=True, null=True, verbose_name="Envoyé le")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Log Email"
        verbose_name_plural = "Logs Emails"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subject} - {self.recipient_email}"


class SMSLog(models.Model):
    """
    Log des SMS (préparation future - non actif).
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        SENT = 'sent', 'Envoyé'
        FAILED = 'failed', 'Échec'
    
    recipient_phone = models.CharField(max_length=20, verbose_name="Téléphone")
    recipient_name = models.CharField(max_length=200, blank=True, verbose_name="Nom")
    
    message = models.TextField(verbose_name="Message")
    
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Log SMS"
        verbose_name_plural = "Logs SMS"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient_phone} - {self.message[:50]}"


class Announcement(models.Model):
    """
    Annonce générale pour tous les utilisateurs.
    """
    title = models.CharField(max_length=200, verbose_name="Titre")
    content = models.TextField(verbose_name="Contenu")
    
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_pinned = models.BooleanField(default=False, verbose_name="Épinglée")
    
    start_date = models.DateField(blank=True, null=True, verbose_name="Afficher à partir de")
    end_date = models.DateField(blank=True, null=True, verbose_name="Afficher jusqu'à")
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='announcements',
        verbose_name="Auteur"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Annonce"
        verbose_name_plural = "Annonces"
        ordering = ['-is_pinned', '-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def is_visible(self):
        from datetime import date
        today = date.today()
        
        if not self.is_active:
            return False
        
        if self.start_date and self.start_date > today:
            return False
        
        if self.end_date and self.end_date < today:
            return False
        
        return True

