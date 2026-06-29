from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'phone', 'blood_group', 'is_donor', 'is_available')
    list_filter = ('is_donor', 'is_available', 'blood_group')
    search_fields = ('username', 'phone')