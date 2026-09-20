from django.contrib import admin

from .models import AppSettings, BackupRecord, RestoreRecord


@admin.register(BackupRecord)
class BackupRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'connection',
        'trigger',
        'scheduled_job',
        'status',
        'engine',
        'download_filename',
        'compressed',
        'size_bytes',
        'created_at',
        'finished_at',
    )
    list_filter = ('status', 'trigger', 'engine', 'compressed')
    search_fields = ('relative_media_path', 'download_filename', 'error_message')
    readonly_fields = ('created_at', 'updated_at', 'finished_at')
    raw_id_fields = ('connection', 'initiated_by', 'scheduled_job')


@admin.register(RestoreRecord)
class RestoreRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'backup', 'connection', 'status', 'engine', 'created_at', 'finished_at')
    list_filter = ('status', 'engine')
    readonly_fields = ('created_at', 'updated_at', 'finished_at')


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'keep_local_backups', 'updated_at')
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        return not AppSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
