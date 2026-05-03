from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone

from dbs import restore as dbs_restore
from dbs.base import BackupRestoreError

from db_connections.services import connection_to_params

from .models import BackupRecord, RestoreRecord


def resolved_backup_file(backup: BackupRecord) -> Path:
    """Return absolute path to backup artifact; raises if outside MEDIA_ROOT or missing."""
    rel = (backup.relative_media_path or '').strip()
    if not rel:
        raise BackupRestoreError('Backup has no stored file path.')
    media_root = Path(settings.MEDIA_ROOT).resolve()
    candidate = (media_root / rel).resolve()
    if not candidate.is_relative_to(media_root):
        raise BackupRestoreError('Invalid backup storage path.')
    return candidate


def perform_restore(
    *,
    backup: BackupRecord,
    initiated_by: Any,
    restore_kwargs: dict[str, Any],
) -> RestoreRecord:
    if backup.status != BackupRecord.Status.SUCCESS:
        raise BackupRestoreError('Only successful backups can be restored.')

    path = resolved_backup_file(backup)
    if not path.is_file():
        raise BackupRestoreError(f'Backup file missing on disk: {backup.relative_media_path}')

    connection = backup.connection
    params = connection_to_params(connection)
    opts = dict(restore_kwargs or {})

    rr = RestoreRecord.objects.create(
        backup=backup,
        connection=connection,
        initiated_by=initiated_by,
        status=RestoreRecord.Status.IN_PROGRESS,
        options=opts,
        engine=backup.engine,
    )

    try:
        dbs_restore(backup.engine, params, src=path, **opts)
        rr.status = RestoreRecord.Status.SUCCESS
        rr.finished_at = timezone.now()
        rr.save(update_fields=['status', 'finished_at', 'updated_at'])
        return rr
    except Exception as e:
        rr.status = RestoreRecord.Status.FAILED
        rr.error_message = str(e)[:8000]
        rr.finished_at = timezone.now()
        rr.save(update_fields=['status', 'error_message', 'finished_at', 'updated_at'])
        if isinstance(e, BackupRestoreError):
            raise
        raise BackupRestoreError(str(e)) from e
