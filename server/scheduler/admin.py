from django.contrib import admin

from .models import ScheduledJob


@admin.register(ScheduledJob)
class ScheduledJobAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'enabled',
        'schedule_kind',
        'task_key',
        'next_run',
        'last_run',
        'last_status',
        'run_as',
    )
    list_filter = ('enabled', 'schedule_kind', 'task_key', 'last_status')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'last_run', 'last_error')
