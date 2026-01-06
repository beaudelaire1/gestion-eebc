"""Admin pour le module Finance."""

from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from .models import FinancialTransaction, FinanceCategory, ReceiptProof, BudgetLine


class ReceiptProofInline(admin.TabularInline):
    """Inline pour les preuves de paiement."""
    model = ReceiptProof
    extra = 1
    fields = ['proof_type', 'image', 'ocr_status', 'notes']
    readonly_fields = ['ocr_status']


@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    """Admin pour les transactions financières."""
    
    list_display = [
        'reference', 'transaction_date', 'transaction_type_badge',
        'amount_display', 'payment_method', 'status_badge', 'member'
    ]
    list_filter = ['transaction_type', 'status', 'payment_method', 'category', 'transaction_date']
    search_fields = ['reference', 'description', 'member__first_name', 'member__last_name']
    date_hierarchy = 'transaction_date'
    
    readonly_fields = ['reference', 'created_at', 'updated_at', 'validated_at']
    autocomplete_fields = ['member', 'event', 'category']
    inlines = [ReceiptProofInline]
    
    fieldsets = (
        ('Transaction', {
            'fields': ('reference', 'transaction_type', 'amount', 'transaction_date')
        }),
        ('Détails', {
            'fields': ('payment_method', 'category', 'description')
        }),
        ('Liens', {
            'fields': ('member', 'event'),
            'classes': ('collapse',)
        }),
        ('Validation', {
            'fields': ('status', 'validated_by', 'validated_at', 'notes')
        }),
        ('Métadonnées', {
            'fields': ('recorded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def transaction_type_badge(self, obj):
        colors = {
            'don': 'success', 'dime': 'success', 'offrande': 'success',
            'depense': 'danger', 'remboursement': 'warning', 'transfert': 'info'
        }
        color = colors.get(obj.transaction_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_transaction_type_display()
        )
    transaction_type_badge.short_description = 'Type'
    
    def amount_display(self, obj):
        color = 'green' if obj.is_income else 'red'
        sign = '+' if obj.is_income else '-'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{} €</span>',
            color, sign, obj.amount
        )
    amount_display.short_description = 'Montant'
    
    def status_badge(self, obj):
        colors = {'en_attente': 'warning', 'valide': 'success', 'annule': 'danger'}
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(FinanceCategory)
class FinanceCategoryAdmin(admin.ModelAdmin):
    """Admin pour les catégories financières."""
    
    list_display = ['name', 'parent', 'is_income', 'budget_annual', 'is_active']
    list_filter = ['is_income', 'is_active', 'parent']
    search_fields = ['name', 'description']
    list_editable = ['is_active']


@admin.register(ReceiptProof)
class ReceiptProofAdmin(admin.ModelAdmin):
    """Admin pour les preuves de paiement."""
    
    list_display = ['transaction', 'proof_type', 'ocr_status_badge', 'ocr_confidence_display', 
                    'uploaded_at', 'uploaded_by']
    list_filter = ['proof_type', 'ocr_status', 'uploaded_at']
    search_fields = ['transaction__reference', 'notes']
    readonly_fields = ['ocr_raw_text', 'ocr_extracted_amount', 'ocr_extracted_date', 
                       'ocr_confidence', 'ocr_processed_at']
    
    actions = ['process_ocr_action']
    
    def ocr_status_badge(self, obj):
        colors = {
            'non_traite': 'secondary',
            'en_cours': 'warning',
            'termine': 'success',
            'echec': 'danger',
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.ocr_status, 'secondary'),
            obj.get_ocr_status_display()
        )
    ocr_status_badge.short_description = 'OCR'
    
    def ocr_confidence_display(self, obj):
        if obj.ocr_confidence:
            color = 'success' if obj.ocr_confidence > 70 else 'warning' if obj.ocr_confidence > 40 else 'danger'
            return format_html(
                '<span class="badge bg-{}">{:.0f}%</span>',
                color, obj.ocr_confidence
            )
        return '-'
    ocr_confidence_display.short_description = 'Confiance'
    
    def process_ocr_action(self, request, queryset):
        """Traite les reçus sélectionnés avec OCR."""
        processed = 0
        for receipt in queryset.filter(ocr_status__in=['non_traite', 'echec']):
            result = receipt.process_ocr()
            if result and 'error' not in result:
                processed += 1
        
        self.message_user(request, f"{processed} reçu(s) traité(s) avec OCR.")
    process_ocr_action.short_description = "Traiter avec OCR"


@admin.register(BudgetLine)
class BudgetLineAdmin(admin.ModelAdmin):
    """Admin pour les lignes budgétaires."""
    
    list_display = ['category', 'year', 'month', 'planned_amount', 
                    'actual_display', 'variance_display']
    list_filter = ['year', 'category']
    
    def actual_display(self, obj):
        return f"{obj.actual_amount} €"
    actual_display.short_description = 'Réel'
    
    def variance_display(self, obj):
        try:
            variance = float(obj.variance)
            variance_percent = float(obj.variance_percent)
        except (ValueError, TypeError):
            variance = 0.0
            variance_percent = 0.0
        color = 'green' if variance >= 0 else 'red'
        return format_html(
            '<span style="color: {};">{:+.2f} € ({:+.1f}%)</span>',
            color, variance, variance_percent
        )
    variance_display.short_description = 'Écart'


# Import des nouveaux modèles
from .models import OnlineDonation, TaxReceipt, Budget, BudgetItem, BudgetCategory, BudgetRequest


@admin.register(OnlineDonation)
class OnlineDonationAdmin(admin.ModelAdmin):
    """Admin pour les dons en ligne."""
    
    list_display = [
        'donor_email', 'amount', 'donation_type', 'status_badge',
        'is_recurring', 'site', 'created_at'
    ]
    list_filter = ['status', 'donation_type', 'is_recurring', 'site', 'created_at']
    search_fields = ['donor_email', 'donor_name', 'stripe_session_id']
    date_hierarchy = 'created_at'
    readonly_fields = [
        'stripe_session_id', 'stripe_payment_intent', 'stripe_subscription_id',
        'transaction', 'created_at', 'completed_at', 'ip_address', 'user_agent'
    ]
    
    fieldsets = (
        ('Donateur', {
            'fields': ('donor_email', 'donor_name', 'member')
        }),
        ('Don', {
            'fields': ('amount', 'donation_type', 'is_recurring', 'recurring_interval', 'site')
        }),
        ('Stripe', {
            'fields': ('stripe_session_id', 'stripe_payment_intent', 'stripe_subscription_id'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('status', 'transaction', 'created_at', 'completed_at')
        }),
        ('Métadonnées', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'completed': 'success',
            'failed': 'danger',
            'refunded': 'info',
            'cancelled': 'secondary',
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'


@admin.register(TaxReceipt)
class TaxReceiptAdmin(admin.ModelAdmin):
    """Admin pour les reçus fiscaux."""
    
    list_display = [
        'receipt_number', 'donor_name', 'fiscal_year', 'total_amount',
        'status_badge', 'issue_date', 'sent_date'
    ]
    list_filter = ['status', 'fiscal_year']
    search_fields = ['receipt_number', 'donor_name', 'donor_email']
    filter_horizontal = ['transactions']
    readonly_fields = ['receipt_number', 'created_at']
    
    fieldsets = (
        ('Reçu', {
            'fields': ('receipt_number', 'fiscal_year', 'status')
        }),
        ('Donateur', {
            'fields': ('donor_name', 'donor_address', 'donor_email', 'member')
        }),
        ('Montant', {
            'fields': ('total_amount', 'transactions')
        }),
        ('Document', {
            'fields': ('pdf_file', 'issue_date', 'sent_date', 'issued_by')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'secondary',
            'issued': 'primary',
            'sent': 'success',
            'cancelled': 'danger',
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    actions = ['generate_pdfs', 'send_by_email']
    
    def generate_pdfs(self, request, queryset):
        for receipt in queryset:
            receipt.generate_pdf()
        self.message_user(request, f"{queryset.count()} PDF(s) généré(s).")
    generate_pdfs.short_description = "Générer les PDF"
    
    def send_by_email(self, request, queryset):
        sent = 0
        for receipt in queryset.filter(status__in=['issued', 'draft']):
            if receipt.donor_email:
                receipt.send_by_email()
                sent += 1
        self.message_user(request, f"{sent} reçu(s) envoyé(s) par email.")
    send_by_email.short_description = "Envoyer par email"


# =============================================================================
# SYSTÈME DE BUDGET
# =============================================================================

class BudgetItemInline(admin.TabularInline):
    """Inline pour les lignes de budget."""
    model = BudgetItem
    extra = 1
    fields = ['category', 'requested_amount', 'approved_amount', 'description', 'priority']
    readonly_fields = []


@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    """Admin pour les catégories de budget."""
    
    list_display = ['name', 'color_display', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 3px; display: inline-block;"></div>',
            obj.color
        )
    color_display.short_description = 'Couleur'


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    """Admin pour les budgets."""
    
    list_display = [
        'name', 'entity_display', 'year', 'status_badge', 
        'total_requested', 'total_approved', 'utilization_display'
    ]
    list_filter = ['status', 'year', 'group', 'department']
    search_fields = ['name', 'description']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'submitted_at', 'approved_at']
    inlines = [BudgetItemInline]
    
    fieldsets = (
        ('Budget', {
            'fields': ('name', 'year', 'description')
        }),
        ('Entité', {
            'fields': ('group', 'department')
        }),
        ('Montants', {
            'fields': ('total_requested', 'total_approved')
        }),
        ('Statut', {
            'fields': ('status', 'created_by', 'approved_by', 'approval_notes')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'submitted_at', 'approved_at'),
            'classes': ('collapse',)
        }),
    )
    
    def entity_display(self, obj):
        entity = obj.entity
        if entity:
            return str(entity)
        return "Non spécifié"
    entity_display.short_description = 'Entité'
    
    def status_badge(self, obj):
        colors = {
            'draft': 'secondary',
            'submitted': 'info',
            'approved': 'success',
            'rejected': 'danger',
            'active': 'primary',
            'closed': 'dark',
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def utilization_display(self, obj):
        try:
            percentage = float(obj.utilization_percentage)
        except (ValueError, TypeError):
            percentage = 0.0
        color = 'success' if percentage < 70 else 'warning' if percentage < 90 else 'danger'
        return format_html(
            '<span class="badge bg-{}">{:.1f}%</span>',
            color, percentage
        )
    utilization_display.short_description = 'Utilisation'


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    """Admin pour les lignes de budget."""
    
    list_display = [
        'budget', 'category', 'requested_amount', 'approved_amount',
        'spent_display', 'utilization_display', 'priority'
    ]
    list_filter = ['category', 'priority', 'budget__year', 'budget__status']
    search_fields = ['budget__name', 'category__name', 'description']
    
    def spent_display(self, obj):
        try:
            amount = float(obj.spent_amount)
        except (ValueError, TypeError):
            amount = 0.0
        return "{:.2f} €".format(amount)
    spent_display.short_description = 'Dépensé'
    
    def utilization_display(self, obj):
        try:
            percentage = float(obj.utilization_percentage)
        except (ValueError, TypeError):
            percentage = 0.0
        color = 'success' if percentage < 70 else 'warning' if percentage < 90 else 'danger'
        return format_html(
            '<span class="badge bg-{}">{:.1f}%</span>',
            color, percentage
        )
    utilization_display.short_description = 'Utilisation'


@admin.register(BudgetRequest)
class BudgetRequestAdmin(admin.ModelAdmin):
    """Admin pour les demandes de budget."""
    
    list_display = [
        'title', 'entity_display', 'category', 'requested_amount',
        'approved_amount', 'urgency_badge', 'status_badge', 'needed_by'
    ]
    list_filter = ['status', 'urgency', 'category', 'created_at']
    search_fields = ['title', 'description']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'reviewed_at']
    
    fieldsets = (
        ('Demande', {
            'fields': ('title', 'description', 'justification')
        }),
        ('Montant', {
            'fields': ('requested_amount', 'approved_amount', 'category')
        }),
        ('Entité', {
            'fields': ('group', 'department')
        }),
        ('Urgence', {
            'fields': ('urgency', 'needed_by')
        }),
        ('Statut', {
            'fields': ('status', 'requested_by', 'reviewed_by', 'review_notes')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'reviewed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def entity_display(self, obj):
        entity = obj.entity
        if entity:
            return str(entity)
        return "Non spécifié"
    entity_display.short_description = 'Entité'
    
    def urgency_badge(self, obj):
        colors = {
            'low': 'secondary',
            'medium': 'info',
            'high': 'warning',
            'urgent': 'danger',
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.urgency, 'secondary'),
            obj.get_urgency_display()
        )
    urgency_badge.short_description = 'Urgence'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'completed': 'primary',
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='approved',
            reviewed_by=request.user,
            approved_amount=models.F('requested_amount')
        )
        self.message_user(request, f"{updated} demande(s) approuvée(s).")
    approve_requests.short_description = "Approuver les demandes sélectionnées"
    
    def reject_requests(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user
        )
        self.message_user(request, f"{updated} demande(s) rejetée(s).")
    reject_requests.short_description = "Rejeter les demandes sélectionnées"