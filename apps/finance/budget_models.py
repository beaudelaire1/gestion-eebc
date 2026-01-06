"""
Modèles pour le système de budget des groupes.
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import date


class BudgetCategory(models.Model):
    """
    Catégorie de budget (ex: Événements, Matériel, Transport, etc.)
    """
    name = models.CharField(max_length=100, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    color = models.CharField(
        max_length=7, 
        default="#0A36FF",
        verbose_name="Couleur",
        help_text="Code couleur hexadécimal pour l'affichage"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    class Meta:
        verbose_name = "Catégorie de budget"
        verbose_name_plural = "Catégories de budget"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Budget(models.Model):
    """
    Budget annuel pour un groupe/département.
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Brouillon'
        SUBMITTED = 'submitted', 'Soumis'
        APPROVED = 'approved', 'Approuvé'
        REJECTED = 'rejected', 'Rejeté'
        ACTIVE = 'active', 'Actif'
        CLOSED = 'closed', 'Clôturé'
    
    # Informations principales
    name = models.CharField(max_length=200, verbose_name="Nom du budget")
    year = models.PositiveIntegerField(verbose_name="Année")
    
    # Groupe/Département concerné
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='budgets',
        verbose_name="Groupe"
    )
    
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='budgets',
        verbose_name="Département"
    )
    
    # Montants
    total_requested = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Montant demandé"
    )
    
    total_approved = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        verbose_name="Montant approuvé"
    )
    
    # Statut et suivi
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Statut"
    )
    
    # Responsables
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_budgets',
        verbose_name="Créé par"
    )
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_budgets',
        verbose_name="Approuvé par"
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Soumis le")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Approuvé le")
    
    # Notes
    description = models.TextField(blank=True, verbose_name="Description")
    approval_notes = models.TextField(blank=True, verbose_name="Notes d'approbation")
    
    class Meta:
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"
        ordering = ['-year', '-created_at']
        unique_together = [
            ['group', 'year'],
            ['department', 'year']
        ]
    
    def __str__(self):
        entity = self.group or self.department
        return f"Budget {self.year} - {entity}"
    
    @property
    def entity(self):
        """Retourne l'entité (groupe ou département) du budget."""
        return self.group or self.department
    
    @property
    def spent_amount(self):
        """Calcule le montant déjà dépensé."""
        return sum(item.spent_amount for item in self.items.all())
    
    @property
    def remaining_amount(self):
        """Calcule le montant restant."""
        return self.total_approved - self.spent_amount
    
    @property
    def utilization_percentage(self):
        """Calcule le pourcentage d'utilisation du budget."""
        if self.total_approved > 0:
            return (self.spent_amount / self.total_approved) * 100
        return 0


class BudgetItem(models.Model):
    """
    Ligne de budget détaillée par catégorie.
    """
    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Budget"
    )
    
    category = models.ForeignKey(
        BudgetCategory,
        on_delete=models.CASCADE,
        verbose_name="Catégorie"
    )
    
    # Montants
    requested_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Montant demandé"
    )
    
    approved_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        verbose_name="Montant approuvé"
    )
    
    # Description et justification
    description = models.TextField(verbose_name="Description")
    justification = models.TextField(blank=True, verbose_name="Justification")
    
    # Priorité
    priority = models.PositiveIntegerField(
        default=1,
        verbose_name="Priorité",
        help_text="1 = Très important, 5 = Peu important"
    )
    
    class Meta:
        verbose_name = "Ligne de budget"
        verbose_name_plural = "Lignes de budget"
        ordering = ['priority', 'category__name']
        unique_together = ['budget', 'category']
    
    def __str__(self):
        return f"{self.budget} - {self.category}"
    
    @property
    def spent_amount(self):
        """Calcule le montant déjà dépensé pour cette ligne."""
        from apps.finance.models import FinancialTransaction
        
        transactions = FinancialTransaction.objects.filter(
            budget_item=self,
            status='valide',
            transaction_type='depense'
        )
        
        return sum(t.amount for t in transactions)
    
    @property
    def remaining_amount(self):
        """Calcule le montant restant pour cette ligne."""
        return self.approved_amount - self.spent_amount
    
    @property
    def utilization_percentage(self):
        """Calcule le pourcentage d'utilisation de cette ligne."""
        if self.approved_amount > 0:
            return (self.spent_amount / self.approved_amount) * 100
        return 0


class BudgetRequest(models.Model):
    """
    Demande de budget ponctuelle (hors budget annuel).
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        APPROVED = 'approved', 'Approuvée'
        REJECTED = 'rejected', 'Rejetée'
        COMPLETED = 'completed', 'Terminée'
    
    class Urgency(models.TextChoices):
        LOW = 'low', 'Faible'
        MEDIUM = 'medium', 'Moyenne'
        HIGH = 'high', 'Élevée'
        URGENT = 'urgent', 'Urgente'
    
    # Informations principales
    title = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(verbose_name="Description")
    
    # Montant
    requested_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Montant demandé"
    )
    
    approved_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        verbose_name="Montant approuvé"
    )
    
    # Catégorie et entité
    category = models.ForeignKey(
        BudgetCategory,
        on_delete=models.CASCADE,
        verbose_name="Catégorie"
    )
    
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='budget_requests',
        verbose_name="Groupe"
    )
    
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='budget_requests',
        verbose_name="Département"
    )
    
    # Urgence et échéance
    urgency = models.CharField(
        max_length=10,
        choices=Urgency.choices,
        default=Urgency.MEDIUM,
        verbose_name="Urgence"
    )
    
    needed_by = models.DateField(
        null=True, blank=True,
        verbose_name="Nécessaire avant le"
    )
    
    # Statut et suivi
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )
    
    # Responsables
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='budget_requests',
        verbose_name="Demandé par"
    )
    
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_budget_requests',
        verbose_name="Examiné par"
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Examiné le")
    
    # Notes
    justification = models.TextField(verbose_name="Justification")
    review_notes = models.TextField(blank=True, verbose_name="Notes d'examen")
    
    class Meta:
        verbose_name = "Demande de budget"
        verbose_name_plural = "Demandes de budget"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.requested_amount}€"
    
    @property
    def entity(self):
        """Retourne l'entité (groupe ou département) de la demande."""
        return self.group or self.department
    
    @property
    def is_overdue(self):
        """Vérifie si la demande est en retard."""
        if self.needed_by and self.status == self.Status.PENDING:
            return date.today() > self.needed_by
        return False