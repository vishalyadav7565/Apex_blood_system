from django.contrib import admin
from ambulance_apps.drivers.models import Driver


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'license_number', 'verification_status', 'is_verified')
    list_filter = ('verification_status', 'is_verified')
    search_fields = ('name', 'phone', 'license_number')
