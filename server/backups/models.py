from __future__ import annotations

from django.conf import settings
from django.db import models


class BackupRecord(models.Model):
    """Audit row when a logical backup file is produced under ``MEDIA_ROOT``."""

    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'In progress'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    class Trigger(models.TextChoices):
        MANUAL = 'manual', 'Manual (API)'
        SCHEDULED = 'scheduled', 'Scheduled job'

    connection = models.ForeignKey(
        'db_connections.DatabaseConnection',
        on_delete=models.CASCADE,
        related_name='backup_records',
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='backup_records_initiated',
    )
    trigger = models.CharField(max_length=16, choices=Trigger.choices, default=Trigger.MANUAL)
    scheduled_job = models.ForeignKey(
        'scheduler.ScheduledJob',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='backup_records',
        help_text='Set when this backup was produced by a schedule (used for retention).',
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.IN_PROGRESS)

    engine = models.CharField(max_length=32)
    relative_media_path = models.CharField(
        max_length=512,
        blank=True,
        default='',
        help_text='Path relative to MEDIA_ROOT (POSIX slashes).',
    )
    download_filename = models.CharField(max_length=255, blank=True, default='')
    size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    compressed = models.BooleanField(
        default=False,
        help_text='True when the stored artifact is gzip (.gz).',
    )
    storage_uploads = models.JSONField(
        default=list,
        blank=True,
        help_text='Per-destination upload results (id, name, kind, ok, relative, remote/error).',
    )
    error_message = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['connection', '-created_at']),
            models.Index(fields=['scheduled_job', '-created_at']),
        ]

    def __str__(self) -> str:
        return f'Backup {self.pk} ({self.connection})'


class RestoreRecord(models.Model):
    """Audit row for each restore attempt against a stored backup file."""

    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'In progress'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    backup = models.ForeignKey(
        BackupRecord,
        on_delete=models.CASCADE,
        related_name='restore_logs',
    )
    connection = models.ForeignKey(
        'db_connections.DatabaseConnection',
        on_delete=models.CASCADE,
        related_name='restore_records',
        help_text='Target connection at restore time (same row as backup.connection).',
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='restore_records_initiated',
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.IN_PROGRESS)

    engine = models.CharField(max_length=32)
    options = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['backup', '-created_at']),
            models.Index(fields=['connection', '-created_at']),
        ]

    def __str__(self) -> str:
        return f'Restore {self.pk} (backup {self.backup_id})'


class AlertEvent(models.Model):
    """Persisted operator alert (errors/warnings) for the dashboard and webhook."""

    class Status(models.TextChoices):
        SUCCESS = 'success', 'Success'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'

    status = models.CharField(max_length=16, choices=Status.choices)
    source = models.CharField(max_length=64, blank=True, default='')
    error = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField()
    context = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'status'], name='backups_ale_created_idx'),
        ]

    def __str__(self) -> str:
        return f'{self.status}: {self.error or self.source or self.pk}'

    @property
    def webhook_status(self) -> str:
        if self.status == self.Status.WARNING:
            return 'degraded'
        if self.status == self.Status.SUCCESS:
            return 'up'
        return 'down'


class AppSettings(models.Model):
    """
    Single-row configuration (pk always 1).

    When ``keep_local_backups`` is False, successful backups that uploaded to at least
    one remote storage are removed from the API server filesystem.
    """

    keep_local_backups = models.BooleanField(
        default=True,
        help_text=(
            'If disabled, drop the local copy after a successful upload to remote storage '
            '(S3/SFTP/FTP). Download and restore then pick a remote (or local if still present).'
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'App settings'
        verbose_name_plural = 'App settings'

    def __str__(self) -> str:
        return 'App settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> 'AppSettings':
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj
