from django.contrib import admin

from .models import BackupRecord, RestoreRecord


@admin.register(BackupRecord)
class BackupRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'connection',
        'trigger',
        'status',
        'engine',
        'download_filename',
        'size_bytes',
        'created_at',
        'finished_at',
    )
    list_filter = ('status', 'trigger', 'engine')
    search_fields = ('relative_media_path', 'download_filename', 'error_message')
    readonly_fields = ('created_at', 'updated_at', 'finished_at')


@admin.register(RestoreRecord)
class RestoreRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'backup', 'connection', 'status', 'engine', 'created_at', 'finished_at')
    list_filter = ('status', 'engine')
    readonly_fields = ('created_at', 'updated_at', 'finished_at')
