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


class EmailTemplate(models.Model):
    """
    Template d'email configurable via l'admin Django.
    """
    class TemplateType(models.TextChoices):
        EVENT_NOTIFICATION = 'event_notification', 'Notification d\'événement'
        EVENT_REMINDER = 'event_reminder', 'Rappel d\'événement'
        EVENT_CANCELLED = 'event_cancelled', 'Événement annulé'
        TRANSPORT_CONFIRMATION = 'transport_confirmation', 'Confirmation de transport'
        WELCOME = 'welcome', 'Bienvenue'
        PASSWORD_RESET = 'password_reset', 'Réinitialisation mot de passe'
        BIRTHDAY = 'birthday', 'Anniversaire'
        DONATION_RECEIPT = 'donation_receipt', 'Reçu de don'
        CUSTOM = 'custom', 'Personnalisé'
    
    name = models.CharField(
        max_length=100,
        verbose_name="Nom du template"
    )
    
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
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    
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
        unique_together = [['template_type', 'is_default']]
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def save(self, *args, **kwargs):
        # S'assurer qu'il n'y a qu'un seul template par défaut par type
        if self.is_default:
            EmailTemplate.objects.filter(
                template_type=self.template_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_default_template(cls, template_type):
        """Récupère le template par défaut pour un type donné."""
        try:
            return cls.objects.get(
                template_type=template_type,
                is_default=True,
                is_active=True
            )
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_template_by_type(cls, template_type, name=None):
        """Récupère un template par type et nom optionnel."""
        queryset = cls.objects.filter(
            template_type=template_type,
            is_active=True
        )
        
        if name:
            try:
                return queryset.get(name=name)
            except cls.DoesNotExist:
                pass
        
        # Fallback sur le template par défaut
        return cls.get_default_template(template_type)


class EmailLog(models.Model):
    """
    Log des emails envoyés avec statut et métadonnées.
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
    
    # Métadonnées pour le suivi
    template_type = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Type de template utilisé",
        help_text="Type de template utilisé pour cet email"
    )
    
    sent_at = models.DateTimeField(blank=True, null=True, verbose_name="Envoyé le")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Log Email"
        verbose_name_plural = "Logs Emails"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['recipient_email', '-created_at']),
            models.Index(fields=['template_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.subject} - {self.recipient_email}"
    
    @property
    def is_successful(self):
        """Retourne True si l'email a été envoyé avec succès."""
        return self.status == self.Status.SENT
    
    @property
    def is_failed(self):
        """Retourne True si l'email a échoué."""
        return self.status == self.Status.FAILED
    
    @property
    def is_pending(self):
        """Retourne True si l'email est en attente."""
        return self.status == self.Status.PENDING
    
    @property
    def delivery_time(self):
        """Retourne le temps de livraison en secondes."""
        if self.sent_at and self.created_at:
            return (self.sent_at - self.created_at).total_seconds()
        return None
    
    @classmethod
    def get_stats(cls, days=30):
        """
        Retourne les statistiques d'envoi des derniers jours.
        
        Args:
            days: Nombre de jours à analyser
            
        Returns:
            dict: Statistiques d'envoi
        """
        from django.utils import timezone
        from django.db.models import Count
        
        since = timezone.now() - timezone.timedelta(days=days)
        
        queryset = cls.objects.filter(created_at__gte=since)
        
        stats = queryset.aggregate(
            total=Count('id'),
            sent=Count('id', filter=models.Q(status=cls.Status.SENT)),
            failed=Count('id', filter=models.Q(status=cls.Status.FAILED)),
            pending=Count('id', filter=models.Q(status=cls.Status.PENDING))
        )
        
        # Calculer les pourcentages
        total = stats['total']
        if total > 0:
            stats['success_rate'] = round((stats['sent'] / total) * 100, 2)
            stats['failure_rate'] = round((stats['failed'] / total) * 100, 2)
        else:
            stats['success_rate'] = 0
            stats['failure_rate'] = 0
        
        return stats
    
    @classmethod
    def get_failed_emails_by_error(cls, days=7):
        """
        Retourne les emails échoués groupés par type d'erreur.
        
        Args:
            days: Nombre de jours à analyser
            
        Returns:
            dict: Erreurs groupées avec compteurs
        """
        from django.utils import timezone
        from django.db.models import Count
        
        since = timezone.now() - timezone.timedelta(days=days)
        
        failed_emails = cls.objects.filter(
            status=cls.Status.FAILED,
            created_at__gte=since
        ).values('error_message').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return {item['error_message']: item['count'] for item in failed_emails}
    
    def retry_send(self):
        """
        Marque l'email pour un nouvel essai d'envoi.
        
        Returns:
            bool: True si l'email peut être renvoyé
        """
        if self.status == self.Status.FAILED:
            self.status = self.Status.PENDING
            self.error_message = ''
            self.save()
            return True
        return False


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

