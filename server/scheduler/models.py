from __future__ import annotations

from datetime import datetime
from datetime import timedelta

from croniter import CroniterBadCronError, croniter
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from db_connections.models import DatabaseConnection

from .tasks import TASK_KEY_CHOICES


class ScheduledJob(models.Model):
    """Declarative schedule rows executed by ``manage.py scheduler_tick``."""

    class ScheduleKind(models.TextChoices):
        INTERVAL = 'interval', 'Every N seconds'
        CRONTAB = 'crontab', 'Cron expression'

    class LastStatus(models.TextChoices):
        PENDING = '', '—'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    name = models.CharField(max_length=128, unique=True)
    enabled = models.BooleanField(default=True)

    schedule_kind = models.CharField(
        max_length=16,
        choices=ScheduleKind.choices,
        default=ScheduleKind.INTERVAL,
    )
    interval_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Used when schedule kind is interval (minimum 60).',
    )
    crontab_expression = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text='Five-part cron, e.g. "15 */6 * * *" (minute hour dom month dow).',
    )

    task_key = models.CharField(max_length=64, choices=TASK_KEY_CHOICES)
    payload = models.JSONField(
        default=dict,
        blank=True,
        help_text='Keyword arguments passed to the task (must be JSON-serializable).',
    )
    run_as = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='scheduler_jobs',
        help_text='Required for backup_saved_connection (scopes DB rows to this user).',
    )

    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(
        max_length=16,
        choices=LastStatus.choices,
        blank=True,
        default='',
    )
    last_error = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['enabled', 'next_run']),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        if self.schedule_kind == self.ScheduleKind.INTERVAL:
            if not self.interval_seconds:
                raise ValidationError({'interval_seconds': 'Interval jobs require a positive interval.'})
            if self.interval_seconds < 60:
                raise ValidationError({'interval_seconds': 'Use at least 60 seconds.'})
            if (self.crontab_expression or '').strip():
                raise ValidationError({'crontab_expression': 'Leave empty for interval schedules.'})
        elif self.schedule_kind == self.ScheduleKind.CRONTAB:
            expr = (self.crontab_expression or '').strip()
            if not expr:
                raise ValidationError({'crontab_expression': 'Cron schedules require an expression.'})
            try:
                croniter(expr)
            except CroniterBadCronError as e:
                raise ValidationError({'crontab_expression': str(e)}) from e
            if self.interval_seconds:
                raise ValidationError({'interval_seconds': 'Leave empty for cron schedules.'})

        if self.task_key == 'backup_saved_connection':
            if self.run_as_id is None:
                raise ValidationError({'run_as': 'Pick the user whose saved connection will be backed up.'})
            cid = self.payload.get('connection_id')
            if cid is None:
                raise ValidationError({'payload': 'Include {"connection_id": <int>} in payload.'})
            if not isinstance(cid, int):
                raise ValidationError({'payload': 'connection_id must be an integer.'})

            try:
                DatabaseConnection.objects.get(pk=cid, user_id=self.run_as_id)
            except DatabaseConnection.DoesNotExist as e:
                raise ValidationError(
                    {'payload': 'connection_id must belong to the selected run_as user.'}
                ) from e

        if self.task_key == 'noop' and self.payload:
            raise ValidationError({'payload': 'No payload keys are used for noop.'})

    def compute_next_run_after(self, base: datetime) -> datetime:
        """Earliest future run strictly after ``base`` for this schedule."""
        if timezone.is_naive(base):
            base = timezone.make_aware(base, timezone.get_current_timezone())

        if self.schedule_kind == self.ScheduleKind.INTERVAL:
            assert self.interval_seconds is not None
            return base + timedelta(seconds=int(self.interval_seconds))

        expr = (self.crontab_expression or '').strip()
        tz = timezone.get_current_timezone()
        itr = croniter(expr, base, tzinfo=tz)
        nxt = itr.get_next(datetime)
        if timezone.is_naive(nxt):
            nxt = timezone.make_aware(nxt, tz)
        return nxt

    def save(self, *args, **kwargs):
        if self.next_run is None:
            self.next_run = self.compute_next_run_after(timezone.now())
        super().save(*args, **kwargs)
