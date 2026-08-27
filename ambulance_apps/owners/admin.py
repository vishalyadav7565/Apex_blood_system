from django.contrib import admin
from ambulance_apps.owners.models import Owner


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone', 'company_name', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('name', 'email', 'phone', 'company_name')
    ordering = ('-created_at',)
