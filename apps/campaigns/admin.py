from django.contrib import admin
from .models import Campaign, Donation


class DonationInline(admin.TabularInline):
    model = Donation
    extra = 1
    readonly_fields = ['created_at']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'goal_amount', 'collected_amount', 'progress_percentage', 
                    'start_date', 'end_date', 'is_active', 'status_display']
    list_filter = ['is_active', 'start_date', 'end_date']
    search_fields = ['name', 'description']
    date_hierarchy = 'start_date'
    inlines = [DonationInline]
    
    def progress_percentage(self, obj):
        return f"{obj.progress_percentage}%"
    progress_percentage.short_description = "Progression"
    
    def status_display(self, obj):
        colors = {
            'success': '🟢',
            'warning': '🟠',
            'danger': '🔴',
            'info': '🔵',
            'primary': '🔷',
            'secondary': '⚪',
        }
        return colors.get(obj.status_color, '⚪')
    status_display.short_description = "Statut"


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'donor_display', 'amount', 'donation_date']
    list_filter = ['campaign', 'is_anonymous', 'donation_date']
    search_fields = ['donor_name', 'campaign__name']
    date_hierarchy = 'donation_date'
    
    def donor_display(self, obj):
        if obj.is_anonymous:
            return "Anonyme"
        return obj.donor_name or "Non spécifié"
    donor_display.short_description = "Donateur"

