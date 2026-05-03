from django.contrib import admin

from .models import StorageDestination


@admin.register(StorageDestination)
class StorageDestinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'user', 'host', 'bucket', 'updated_at')
    list_filter = ('kind',)
    search_fields = ('name', 'user__username', 'host', 'bucket')
    readonly_fields = ('created_at', 'updated_at')
