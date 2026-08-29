from django.contrib import admin
from .models import DriverProfile, TransportRequest, DriverLiveLocation


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'vehicle_type', 'capacity', 'zone', 'is_available']
    list_filter = ['is_available', 'available_sunday', 'available_week', 'zone']
    search_fields = ['user__first_name', 'user__last_name', 'vehicle_model', 'zone']


@admin.register(TransportRequest)
class TransportRequestAdmin(admin.ModelAdmin):
    list_display = ['requester_name', 'event_date', 'event_time', 'driver', 'status']
    list_filter = ['status', 'event_date']
    search_fields = ['requester_name', 'requester_phone', 'pickup_address']
    date_hierarchy = 'event_date'
    
    autocomplete_fields = ['driver']


@admin.register(DriverLiveLocation)
class DriverLiveLocationAdmin(admin.ModelAdmin):
    list_display = ['transport_request', 'driver', 'latitude', 'longitude', 'is_active', 'recorded_at', 'updated_at']
    list_filter = ['is_active', 'recorded_at']
    search_fields = ['transport_request__requester_name', 'driver__user__first_name', 'driver__user__last_name']

