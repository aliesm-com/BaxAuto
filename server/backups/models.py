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
    error_message = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['connection', '-created_at']),
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
