"""Drop backup/restore rows stuck in ``in_progress`` longer than a threshold."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone

from backups.models import BackupRecord, RestoreRecord
from baxconf.alertlog import log_alert

# Jobs left ``in_progress`` longer than this are treated as dead and removed.
STALE_IN_PROGRESS_AFTER = timedelta(hours=1)


def _unlink_media_if_present(relative_media_path: str) -> None:
    rel = (relative_media_path or '').strip()
    if not rel:
        return
    media_root = Path(settings.MEDIA_ROOT).resolve()
    candidate = (media_root / rel).resolve()
    try:
        if candidate.is_relative_to(media_root) and candidate.is_file():
            candidate.unlink()
    except OSError:
        pass


def cancel_in_progress_backup(
    record: BackupRecord,
    *,
    reason: str = 'Cancelled manually.',
    cancelled_by: Any = None,
) -> None:
    """Stop and delete an ``in_progress`` backup row; raise ``ValueError`` if not eligible."""
    if record.status != BackupRecord.Status.IN_PROGRESS:
        raise ValueError('Only in-progress backups can be cancelled.')
    name = getattr(record.connection, 'name', None) or f'connection#{record.connection_id}'
    job_name = getattr(record.scheduled_job, 'name', None) or ''
    _unlink_media_if_present(record.relative_media_path)
    pk = record.pk
    connection_id = record.connection_id
    actor = getattr(cancelled_by, 'username', None) or getattr(cancelled_by, 'pk', None)
    record.delete()
    detail = f'backup #{pk} on “{name}”'
    if job_name:
        detail += f' (schedule “{job_name}”)'
    msg = f'In-progress {detail} stopped and removed. {reason}'.strip()
    log_alert(
        msg,
        status='warning',
        source='backup',
        connection_id=connection_id,
        backup_id=pk,
        cancelled_by=actor,
    )


def cancel_in_progress_restore(
    record: RestoreRecord,
    *,
    reason: str = 'Cancelled manually.',
    cancelled_by: Any = None,
) -> None:
    """Stop and delete an ``in_progress`` restore row; raise ``ValueError`` if not eligible."""
    if record.status != RestoreRecord.Status.IN_PROGRESS:
        raise ValueError('Only in-progress restores can be cancelled.')
    name = getattr(record.connection, 'name', None) or f'connection#{record.connection_id}'
    pk = record.pk
    connection_id = record.connection_id
    backup_id = record.backup_id
    actor = getattr(cancelled_by, 'username', None) or getattr(cancelled_by, 'pk', None)
    record.delete()
    log_alert(
        f'In-progress restore #{pk} on “{name}” stopped and removed. {reason}'.strip(),
        status='warning',
        source='restore',
        connection_id=connection_id,
        restore_id=pk,
        backup_id=backup_id,
        cancelled_by=actor,
    )


def sweep_stale_in_progress(*, older_than: timedelta | None = None) -> int:
    """
    Delete backup and restore records stuck in ``in_progress`` past ``older_than``.

    Emits a warning alert per removed row. Returns the number of rows deleted.
    """
    age = older_than if older_than is not None else STALE_IN_PROGRESS_AFTER
    cutoff = timezone.now() - age
    removed = 0

    stale_backups = list(
        BackupRecord.objects.filter(
            status=BackupRecord.Status.IN_PROGRESS,
            created_at__lt=cutoff,
        )
        .select_related('connection', 'scheduled_job')
        .order_by('created_at')
    )
    for record in stale_backups:
        age_minutes = int((timezone.now() - record.created_at).total_seconds() // 60)
        cancel_in_progress_backup(
            record,
            reason=f'Auto-removed after {age_minutes} minute(s) stuck in progress.',
        )
        removed += 1

    stale_restores = list(
        RestoreRecord.objects.filter(
            status=RestoreRecord.Status.IN_PROGRESS,
            created_at__lt=cutoff,
        )
        .select_related('connection')
        .order_by('created_at')
    )
    for record in stale_restores:
        age_minutes = int((timezone.now() - record.created_at).total_seconds() // 60)
        cancel_in_progress_restore(
            record,
            reason=f'Auto-removed after {age_minutes} minute(s) stuck in progress.',
        )
        removed += 1

    return removed
