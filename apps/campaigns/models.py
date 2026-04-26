from django.db import models
from django.conf import settings
from decimal import Decimal


class Campaign(models.Model):
    """
    Modèle représentant une campagne de collecte de fonds.
    """
    
    class NotificationScope(models.TextChoices):
        NONE = 'none', 'Aucune notification'
        ALL = 'all', 'Tout le monde'
        MEMBERS = 'members', 'Tous les membres'
        STAFF = 'staff', 'Direction (pasteurs, diacres, anciens)'
        GROUP = 'group', 'Un groupe spécifique'
    
    name = models.CharField(max_length=200, verbose_name="Nom de la campagne")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Site d'appartenance (multi-sites)
    site = models.ForeignKey(
        'core.Site',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns',
        verbose_name="Site",
        help_text="Laisser vide pour une campagne globale"
    )
    
    goal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Objectif (€)"
    )
    collected_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant collecté (€)"
    )
    
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(verbose_name="Date de fin")
    
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns',
        verbose_name="Responsable"
    )
    
    # Portée des notifications
    notification_scope = models.CharField(
        max_length=15,
        choices=NotificationScope.choices,
        default=NotificationScope.MEMBERS,
        verbose_name="Portée des notifications",
        help_text="Qui doit être notifié de cette campagne"
    )
    
    # Groupe spécifique (si scope = group)
    target_group = models.ForeignKey(
        'groups.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='targeted_campaigns',
        verbose_name="Groupe cible",
        help_text="Requis si la portée est 'Un groupe spécifique'"
    )
    
    notification_sent = models.BooleanField(default=False, verbose_name="Notification envoyée")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Campagne"
        verbose_name_plural = "Campagnes"
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.progress_percentage}%)"
    
    @property
    def progress_percentage(self):
        if self.goal_amount > 0:
            return int((self.collected_amount / self.goal_amount) * 100)
        return 0
    
    @property
    def remaining_amount(self):
        return max(self.goal_amount - self.collected_amount, Decimal('0'))
    
    @property
    def status_color(self):
        """Couleur automatique selon le statut."""
        from datetime import date
        today = date.today()
        
        if not self.is_active:
            return 'secondary'  # Gris - Inactif
        
        if self.collected_amount >= self.goal_amount:
            return 'success'  # Vert - Objectif atteint
        
        if self.end_date < today:
            return 'danger'  # Rouge - Deadline dépassée
        
        days_remaining = (self.end_date - today).days
        if days_remaining <= 7:
            return 'warning'  # Orange - Moins d'une semaine
        
        if self.progress_percentage >= 75:
            return 'info'  # Bleu - Bonne progression
        
        return 'primary'  # Bleu foncé - En cours
    
    @property
    def is_critical(self):
        """Campagne critique si deadline proche et objectif loin."""
        from datetime import date
        today = date.today()
        
        if not self.is_active or self.collected_amount >= self.goal_amount:
            return False
        
        days_remaining = (self.end_date - today).days
        return days_remaining <= 14 and self.progress_percentage < 50
    
    def get_notification_recipients(self):
        """Retourne les emails des personnes à notifier selon la portée."""
        from apps.accounts.models import User
        from apps.members.models import Member
        
        emails = set()
        
        if self.notification_scope == self.NotificationScope.NONE:
            return []
        
        if self.notification_scope == self.NotificationScope.ALL:
            for user in User.objects.filter(is_active=True).exclude(email=''):
                emails.add(user.email)
            for member in Member.objects.exclude(email='').exclude(email__isnull=True):
                emails.add(member.email)
        
        elif self.notification_scope == self.NotificationScope.MEMBERS:
            for member in Member.objects.filter(status='actif').exclude(email='').exclude(email__isnull=True):
                emails.add(member.email)
        
        elif self.notification_scope == self.NotificationScope.STAFF:
            staff_roles = ['pasteur', 'ancien', 'diacre', 'admin']
            for user in User.objects.filter(is_active=True).exclude(email=''):
                if any(r in user.role for r in staff_roles) or user.is_superuser:
                    emails.add(user.email)
        
        elif self.notification_scope == self.NotificationScope.GROUP:
            if self.target_group:
                for member in self.target_group.members.all():
                    if member.email:
                        emails.add(member.email)
        
        return list(emails)


class Donation(models.Model):
    """
    Modèle représentant un don à une campagne.
    """
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='donations',
        verbose_name="Campagne"
    )
    
    donor_name = models.CharField(max_length=200, blank=True, verbose_name="Nom du donateur")
    is_anonymous = models.BooleanField(default=False, verbose_name="Don anonyme")
    
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant (€)")
    donation_date = models.DateField(auto_now_add=True, verbose_name="Date du don")
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    is_cancelled = models.BooleanField(default=False, verbose_name="Annulé")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Don"
        verbose_name_plural = "Dons"
        ordering = ['-donation_date']
    
    def __str__(self):
        donor = "Anonyme" if self.is_anonymous else (self.donor_name or "Inconnu")
        status = " (Annulé)" if self.is_cancelled else ""
        return f"{donor} - {self.amount}€{status}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        was_cancelled = False
        prev_amount = Decimal('0')
        
        if not is_new:
            old_inst = Donation.objects.filter(pk=self.pk).first()
            if old_inst:
                was_cancelled = old_inst.is_cancelled
                prev_amount = old_inst.amount
        
        super().save(*args, **kwargs)
        
        # Mise à jour du montant collecté
        campaign = self.campaign
        impact = Decimal('0')
        
        if self.is_cancelled:
            # Si annulé maintenant
            if not was_cancelled:
                # Vient d'être annulé : on soustrait l'ancien montant
                impact = -prev_amount
        else:
            # Si actif maintenant
            if was_cancelled:
                # Vient d'être réactivé : on ajoute le montant actuel
                impact = self.amount
            else:
                # Était actif et reste actif : on ajuste la différence
                impact = self.amount - prev_amount
                
        if impact != 0:
            campaign.collected_amount += impact
            campaign.save(update_fields=['collected_amount'])
    
    def delete(self, *args, **kwargs):
        campaign = self.campaign
        amount = self.amount
        super().delete(*args, **kwargs)
        # Décrémenter le montant collecté
        campaign.collected_amount = max(campaign.collected_amount - amount, 0)
        campaign.save(update_fields=['collected_amount'])

