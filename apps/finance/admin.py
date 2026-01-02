"""Admin pour le module Finance."""

from django.contrib import admin
from django.utils.html import format_html
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
    
    list_display = ['transaction', 'proof_type', 'ocr_status', 'uploaded_at', 'uploaded_by']
    list_filter = ['proof_type', 'ocr_status', 'uploaded_at']
    search_fields = ['transaction__reference', 'notes']
    readonly_fields = ['ocr_raw_text', 'ocr_extracted_amount', 'ocr_extracted_date', 
                       'ocr_confidence', 'ocr_processed_at']


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
        variance = obj.variance
        color = 'green' if variance >= 0 else 'red'
        return format_html(
            '<span style="color: {};">{:+.2f} € ({:+.1f}%)</span>',
            color, variance, obj.variance_percent
        )
    variance_display.short_description = 'Écart'


# Import des nouveaux modèles
from .models import OnlineDonation, TaxReceipt


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
