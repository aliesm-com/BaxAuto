from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('App roles', {'fields': ('is_viewer', 'is_editor', 'is_admin')}),
        ('Contact', {'fields': ('phone_number', 'country_code')}),
    )
    list_display = (
        *DjangoUserAdmin.list_display,
        'is_viewer',
        'is_editor',
        'is_admin',
        'phone_number',
        'country_code',
    )
