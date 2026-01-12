"""
Models for the API module.
"""
from django.db import models
from django.conf import settings


class DeviceToken(models.Model):
    """
    Device token for push notifications.
    
    Stores FCM/APNs tokens for sending push notifications to mobile devices.
    """
    
    class Platform(models.TextChoices):
        IOS = 'ios', 'iOS'
        ANDROID = 'android', 'Android'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens',
        verbose_name="Utilisateur"
    )
    
    token = models.CharField(
        max_length=500,
        verbose_name="Token",
        help_text="FCM or APNs device token"
    )
    
    platform = models.CharField(
        max_length=10,
        choices=Platform.choices,
        verbose_name="Plateforme"
    )
    
    device_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nom de l'appareil"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Token d'appareil"
        verbose_name_plural = "Tokens d'appareils"
        unique_together = ['user', 'token']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.platform} ({self.device_name or 'Unknown'})"


class AnnouncementReadStatus(models.Model):
    """
    Tracks which announcements have been read by which users.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='announcement_reads',
        verbose_name="Utilisateur"
    )
    
    announcement = models.ForeignKey(
        'communication.Announcement',
        on_delete=models.CASCADE,
        related_name='read_statuses',
        verbose_name="Annonce"
    )
    
    read_at = models.DateTimeField(auto_now_add=True, verbose_name="Lu le")
    
    class Meta:
        verbose_name = "Statut de lecture"
        verbose_name_plural = "Statuts de lecture"
        unique_together = ['user', 'announcement']
    
    def __str__(self):
        return f"{self.user.username} - {self.announcement.title}"
