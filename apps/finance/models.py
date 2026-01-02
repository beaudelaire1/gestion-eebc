"""
Module Finance - Modèles pour la gestion financière.

Ce module gère :
- Les transactions financières (dons, dépenses)
- Les preuves de paiement (reçus, factures)
- Préparation pour OCR futur
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class FinancialTransaction(models.Model):
    """
    Transaction financière de l'église.
    
    Représente tout mouvement d'argent : don reçu, dépense effectuée,
    virement, etc. Chaque transaction peut être liée à une preuve.
    """
    
    class TransactionType(models.TextChoices):
        DON = 'don', 'Don'
        DIME = 'dime', 'Dîme'
        OFFRANDE = 'offrande', 'Offrande'
        DEPENSE = 'depense', 'Dépense'
        REMBOURSEMENT = 'remboursement', 'Remboursement'
        TRANSFERT = 'transfert', 'Transfert'
    
    class PaymentMethod(models.TextChoices):
        ESPECES = 'especes', 'Espèces'
        CHEQUE = 'cheque', 'Chèque'
        VIREMENT = 'virement', 'Virement bancaire'
        CARTE = 'carte', 'Carte bancaire'
        MOBILE = 'mobile', 'Paiement mobile'
        AUTRE = 'autre', 'Autre'
    
    class Status(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        VALIDE = 'valide', 'Validé'
        ANNULE = 'annule', 'Annulé'
    
    # Informations principales
    reference = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name="Référence",
        help_text="Générée automatiquement si vide"
    )
    
    # Site d'appartenance (multi-sites)
    site = models.ForeignKey(
        'core.Site',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name="Site"
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant (€)"
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name="Type de transaction"
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.ESPECES,
        verbose_name="Méthode de paiement"
    )
    
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.EN_ATTENTE,
        verbose_name="Statut"
    )
    
    # Dates
    transaction_date = models.DateField(verbose_name="Date de transaction")
    
    # Description et catégorisation
    description = models.TextField(blank=True, verbose_name="Description")
    category = models.ForeignKey(
        'FinanceCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name="Catégorie"
    )
    
    # Liens optionnels
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name="Membre concerné",
        help_text="Pour les dons/dîmes nominatifs"
    )
    
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name="Événement lié"
    )
    
    # Traçabilité
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_transactions',
        verbose_name="Enregistré par"
    )
    
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_transactions',
        verbose_name="Validé par"
    )
    
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de validation"
    )
    
    # Métadonnées
    notes = models.TextField(blank=True, verbose_name="Notes internes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['transaction_date']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.get_transaction_type_display()} {self.amount}€"
    
    def save(self, *args, **kwargs):
        """Génère une référence unique si absente."""
        if not self.reference:
            self.reference = self._generate_reference()
        super().save(*args, **kwargs)
    
    def _generate_reference(self):
        """Génère une référence au format TRX-YYYYMM-XXXX."""
        from django.utils import timezone
        import random
        import string
        
        now = timezone.now()
        prefix = f"TRX-{now.strftime('%Y%m')}"
        suffix = ''.join(random.choices(string.digits, k=4))
        return f"{prefix}-{suffix}"
    
    @property
    def is_income(self):
        """Retourne True si c'est une entrée d'argent."""
        return self.transaction_type in [
            self.TransactionType.DON,
            self.TransactionType.DIME,
            self.TransactionType.OFFRANDE,
        ]
    
    @property
    def signed_amount(self):
        """Montant signé (positif pour entrées, négatif pour sorties)."""
        if self.is_income:
            return self.amount
        return -self.amount


class FinanceCategory(models.Model):
    """
    Catégorie pour classifier les transactions.
    
    Exemples : Électricité, Fournitures, Missions, Entretien...
    """
    name = models.CharField(max_length=100, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    
    is_income = models.BooleanField(
        default=False,
        verbose_name="Catégorie de revenus",
        help_text="Cocher si cette catégorie concerne des entrées d'argent"
    )
    
    budget_annual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Budget annuel prévu"
    )
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories',
        verbose_name="Catégorie parente"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    class Meta:
        verbose_name = "Catégorie financière"
        verbose_name_plural = "Catégories financières"
        ordering = ['name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class ReceiptProof(models.Model):
    """
    Preuve de paiement (photo de reçu, facture, ticket).
    
    Conçu pour stocker les images de justificatifs avec
    préparation pour traitement OCR futur.
    """
    
    class ProofType(models.TextChoices):
        RECU = 'recu', 'Reçu'
        FACTURE = 'facture', 'Facture'
        TICKET = 'ticket', 'Ticket de caisse'
        RELEVE = 'releve', 'Relevé bancaire'
        AUTRE = 'autre', 'Autre document'
    
    class OCRStatus(models.TextChoices):
        NON_TRAITE = 'non_traite', 'Non traité'
        EN_COURS = 'en_cours', 'En cours'
        TERMINE = 'termine', 'Terminé'
        ECHEC = 'echec', 'Échec'
    
    transaction = models.ForeignKey(
        FinancialTransaction,
        on_delete=models.CASCADE,
        related_name='proofs',
        verbose_name="Transaction"
    )
    
    proof_type = models.CharField(
        max_length=20,
        choices=ProofType.choices,
        default=ProofType.RECU,
        verbose_name="Type de document"
    )
    
    # Image du justificatif
    image = models.ImageField(
        upload_to='finance/proofs/%Y/%m/',
        verbose_name="Image du justificatif"
    )
    
    # Données OCR (pour futur traitement)
    ocr_status = models.CharField(
        max_length=15,
        choices=OCRStatus.choices,
        default=OCRStatus.NON_TRAITE,
        verbose_name="Statut OCR"
    )
    
    ocr_raw_text = models.TextField(
        blank=True,
        verbose_name="Texte OCR brut",
        help_text="Texte extrait automatiquement de l'image"
    )
    
    ocr_extracted_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montant extrait (OCR)"
    )
    
    ocr_extracted_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date extraite (OCR)"
    )
    
    ocr_confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Confiance OCR (%)",
        help_text="Score de confiance de l'extraction"
    )
    
    ocr_processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Traité le"
    )
    
    # Métadonnées
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_proofs',
        verbose_name="Uploadé par"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'upload")
    
    class Meta:
        verbose_name = "Preuve de paiement"
        verbose_name_plural = "Preuves de paiement"
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.get_proof_type_display()} - {self.transaction.reference}"
    
    def process_ocr(self):
        """
        Traite l'image avec OCR pour extraire les informations.
        
        Utilise Tesseract OCR pour extraire montants et dates.
        
        Returns:
            dict: Données extraites ou None si échec
        """
        from .ocr_service import ocr_service
        return ocr_service.process_receipt(self)


class BudgetLine(models.Model):
    """
    Ligne budgétaire pour le suivi prévisionnel.
    
    Permet de définir un budget par catégorie et par période,
    puis de comparer avec les dépenses réelles.
    """
    
    category = models.ForeignKey(
        FinanceCategory,
        on_delete=models.CASCADE,
        related_name='budget_lines',
        verbose_name="Catégorie"
    )
    
    year = models.PositiveIntegerField(verbose_name="Année")
    month = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Mois",
        help_text="Laisser vide pour un budget annuel"
    )
    
    planned_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant prévu"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Ligne budgétaire"
        verbose_name_plural = "Lignes budgétaires"
        unique_together = ['category', 'year', 'month']
        ordering = ['-year', 'month', 'category__name']
    
    def __str__(self):
        period = f"{self.year}"
        if self.month:
            period = f"{self.month:02d}/{self.year}"
        return f"{self.category.name} - {period} : {self.planned_amount}€"
    
    @property
    def actual_amount(self):
        """Calcule le montant réel dépensé/reçu pour cette ligne."""
        from django.db.models import Sum
        
        filters = {
            'category': self.category,
            'transaction_date__year': self.year,
            'status': FinancialTransaction.Status.VALIDE,
        }
        
        if self.month:
            filters['transaction_date__month'] = self.month
        
        result = FinancialTransaction.objects.filter(**filters).aggregate(
            total=Sum('amount')
        )
        
        return result['total'] or Decimal('0.00')
    
    @property
    def variance(self):
        """Écart entre prévu et réel."""
        return self.actual_amount - self.planned_amount
    
    @property
    def variance_percent(self):
        """Écart en pourcentage."""
        if self.planned_amount == 0:
            return 0
        return (self.variance / self.planned_amount) * 100


# =============================================================================
# DONS EN LIGNE (STRIPE)
# =============================================================================

class OnlineDonation(models.Model):
    """
    Don effectué en ligne via Stripe.
    
    Stocke les informations spécifiques aux paiements en ligne
    et fait le lien avec la transaction financière.
    """
    
    class DonationType(models.TextChoices):
        DON = 'don', 'Don'
        DIME = 'dime', 'Dîme'
        OFFRANDE = 'offrande', 'Offrande'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        COMPLETED = 'completed', 'Complété'
        FAILED = 'failed', 'Échoué'
        REFUNDED = 'refunded', 'Remboursé'
        CANCELLED = 'cancelled', 'Annulé'
    
    # Identifiants Stripe
    stripe_session_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="ID Session Stripe"
    )
    stripe_payment_intent = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="ID Payment Intent"
    )
    stripe_subscription_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="ID Abonnement",
        help_text="Pour les dons récurrents"
    )
    
    # Montant et type
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))],
        verbose_name="Montant (€)"
    )
    
    donation_type = models.CharField(
        max_length=20,
        choices=DonationType.choices,
        default=DonationType.DON,
        verbose_name="Type de don"
    )
    
    is_recurring = models.BooleanField(
        default=False,
        verbose_name="Don récurrent"
    )
    
    recurring_interval = models.CharField(
        max_length=10,
        blank=True,
        choices=[('month', 'Mensuel'), ('year', 'Annuel')],
        verbose_name="Fréquence"
    )
    
    # Donateur
    donor_email = models.EmailField(verbose_name="Email du donateur")
    donor_name = models.CharField(max_length=200, blank=True, verbose_name="Nom du donateur")
    
    # Liens
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='online_donations',
        verbose_name="Membre"
    )
    
    site = models.ForeignKey(
        'core.Site',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='online_donations',
        verbose_name="Site"
    )
    
    transaction = models.OneToOneField(
        FinancialTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='online_donation',
        verbose_name="Transaction"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )
    
    # Métadonnées
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Complété le")
    
    class Meta:
        verbose_name = "Don en ligne"
        verbose_name_plural = "Dons en ligne"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.donor_email} - {self.amount}€ ({self.get_status_display()})"


class TaxReceipt(models.Model):
    """
    Reçu fiscal pour les dons.
    
    Génère des reçus fiscaux numérotés conformes à la réglementation
    française pour les dons aux associations cultuelles.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Brouillon'
        ISSUED = 'issued', 'Émis'
        SENT = 'sent', 'Envoyé'
        CANCELLED = 'cancelled', 'Annulé'
    
    # Numérotation
    receipt_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Numéro de reçu"
    )
    
    fiscal_year = models.PositiveIntegerField(verbose_name="Année fiscale")
    
    # Donateur
    donor_name = models.CharField(max_length=200, verbose_name="Nom du donateur")
    donor_address = models.TextField(verbose_name="Adresse du donateur")
    donor_email = models.EmailField(blank=True, verbose_name="Email")
    
    # Membre lié (optionnel)
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tax_receipts',
        verbose_name="Membre"
    )
    
    # Montant total des dons
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant total"
    )
    
    # Transactions incluses
    transactions = models.ManyToManyField(
        FinancialTransaction,
        related_name='tax_receipts',
        verbose_name="Transactions"
    )
    
    # Statut
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Statut"
    )
    
    # PDF généré
    pdf_file = models.FileField(
        upload_to='finance/tax_receipts/%Y/',
        blank=True,
        null=True,
        verbose_name="Fichier PDF"
    )
    
    # Dates
    issue_date = models.DateField(null=True, blank=True, verbose_name="Date d'émission")
    sent_date = models.DateField(null=True, blank=True, verbose_name="Date d'envoi")
    
    # Métadonnées
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='issued_tax_receipts',
        verbose_name="Émis par"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Reçu fiscal"
        verbose_name_plural = "Reçus fiscaux"
        ordering = ['-fiscal_year', '-receipt_number']
    
    def __str__(self):
        return f"Reçu {self.receipt_number} - {self.donor_name} ({self.total_amount}€)"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = self._generate_receipt_number()
        super().save(*args, **kwargs)
    
    def _generate_receipt_number(self):
        """Génère un numéro de reçu unique."""
        import datetime
        
        year = self.fiscal_year or datetime.date.today().year
        
        # Compter les reçus existants pour cette année
        count = TaxReceipt.objects.filter(fiscal_year=year).count() + 1
        
        return f"RF-{year}-{count:04d}"
    
    def generate_pdf(self):
        """Génère le PDF du reçu fiscal."""
        from .pdf_service import save_tax_receipt_pdf
        return save_tax_receipt_pdf(self)
    
    def send_by_email(self):
        """Envoie le reçu par email."""
        from apps.communication.notification_service import notification_service
        from django.utils import timezone
        
        if not self.pdf_file:
            self.generate_pdf()
        
        message = f"""Reçu fiscal {self.receipt_number}

Cher(e) {self.donor_name},

Veuillez trouver ci-joint votre reçu fiscal pour l'année {self.fiscal_year}.

Montant total des dons : {self.total_amount}€

Ce document vous permet de bénéficier d'une réduction d'impôt 
conformément à l'article 200 du Code Général des Impôts.

Merci pour votre générosité.

EEBC - Église Évangélique Baptiste de Cabassou
"""
        
        # TODO: Ajouter la pièce jointe PDF
        notification_service.send_notification(
            recipient={'email': self.donor_email, 'name': self.donor_name},
            message=message,
            subject=f"Reçu fiscal {self.receipt_number} - EEBC",
            channels=['email']
        )
        
        self.status = self.Status.SENT
        self.sent_date = timezone.now().date()
        self.save()
