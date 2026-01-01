from django.db import models
from django.conf import settings
from decimal import Decimal


class Campaign(models.Model):
    """
    Modèle représentant une campagne de collecte de fonds.
    """
    name = models.CharField(max_length=200, verbose_name="Nom de la campagne")
    description = models.TextField(blank=True, verbose_name="Description")
    
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
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Don"
        verbose_name_plural = "Dons"
        ordering = ['-donation_date']
    
    def __str__(self):
        donor = "Anonyme" if self.is_anonymous else (self.donor_name or "Inconnu")
        return f"{donor} - {self.amount}€"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_amount = None
        if not is_new:
            old_donation = Donation.objects.filter(pk=self.pk).first()
            if old_donation:
                old_amount = old_donation.amount
        
        super().save(*args, **kwargs)
        
        # Mise à jour incrémentale du montant collecté
        if is_new:
            self.campaign.collected_amount += self.amount
        elif old_amount is not None:
            self.campaign.collected_amount += (self.amount - old_amount)
        self.campaign.save(update_fields=['collected_amount'])
    
    def delete(self, *args, **kwargs):
        campaign = self.campaign
        amount = self.amount
        super().delete(*args, **kwargs)
        # Décrémenter le montant collecté
        campaign.collected_amount = max(campaign.collected_amount - amount, 0)
        campaign.save(update_fields=['collected_amount'])

