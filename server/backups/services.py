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


def backup_artifact_bytes_on_disk_or_record(
    *,
    relative_media_path: str,
    size_bytes: int | None,
) -> int:
    """
    Bytes to count toward dashboard storage.

    Prefer the current file size on disk when the artifact exists under MEDIA_ROOT;
    otherwise fall back to the persisted ``size_bytes`` (e.g. missing file or legacy rows).
    """
    rel = (relative_media_path or '').strip()
    if rel:
        try:
            media_root = Path(settings.MEDIA_ROOT).resolve()
            candidate = (media_root / rel).resolve()
            if candidate.is_relative_to(media_root) and candidate.is_file():
                return candidate.stat().st_size
        except OSError:
            pass
    return int(size_bytes or 0)


def total_success_backup_storage_bytes(qs) -> int:
    """Sum storage contributions for successful backups in queryset ``qs``."""
    rows = (
        qs.filter(status=BackupRecord.Status.SUCCESS)
        .select_related(None)
        .only('relative_media_path', 'size_bytes')
        .iterator(chunk_size=256)
    )
    return sum(
        backup_artifact_bytes_on_disk_or_record(
            relative_media_path=b.relative_media_path,
            size_bytes=b.size_bytes,
        )
        for b in rows
    )


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
