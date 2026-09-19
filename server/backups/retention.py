"""Delete expired scheduled backups (local media + remote storages)."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from backups.models import BackupRecord
from storage.models import StorageDestination
from storage.transfer import StorageTransferError, delete_backup_file

logger = logging.getLogger(__name__)


def remote_relative_from_media(relative_media_path: str) -> str | None:
    """
    ``db_exports/<user>/<db_slug>/<run_subdir>/<file>`` → ``<db_slug>/<run_subdir>/<file>``.
    """
    parts = [p for p in (relative_media_path or '').replace('\\', '/').strip('/').split('/') if p]
    if len(parts) >= 5 and parts[0] == 'db_exports':
        return '/'.join(parts[2:])
    return None


def prune_schedule_backups(scheduled_job_id: int, *, retention_days: int | None) -> int:
    """
    Remove successful backups for this schedule older than ``retention_days``.

    Returns the number of backup records deleted. No-op when retention is unset.
    """
    if retention_days is None or retention_days < 1:
        return 0

    cutoff = timezone.now() - timedelta(days=int(retention_days))
    qs = (
        BackupRecord.objects.filter(
            scheduled_job_id=scheduled_job_id,
            status=BackupRecord.Status.SUCCESS,
            created_at__lt=cutoff,
        )
        .order_by('created_at')
        .only('id', 'relative_media_path', 'storage_uploads', 'download_filename')
    )

    media_root = Path(settings.MEDIA_ROOT).resolve()
    deleted = 0

    for record in qs.iterator(chunk_size=50):
        remote_rel = remote_relative_from_media(record.relative_media_path)
        uploads = record.storage_uploads if isinstance(record.storage_uploads, list) else []

        for entry in uploads:
            if not entry.get('ok'):
                continue
            dest_id = entry.get('id')
            if not isinstance(dest_id, int):
                continue
            rel = remote_rel
            stored_rel = entry.get('relative')
            if isinstance(stored_rel, str) and stored_rel.strip():
                rel = stored_rel.strip()
            if not rel:
                continue
            try:
                dest = StorageDestination.objects.get(pk=dest_id)
            except StorageDestination.DoesNotExist:
                continue
            try:
                delete_backup_file(dest, rel)
            except (StorageTransferError, OSError) as e:
                logger.warning(
                    'Retention: failed to delete remote backup job=%s dest=%s path=%s: %s',
                    scheduled_job_id,
                    dest_id,
                    rel,
                    e,
                )

        rel_media = (record.relative_media_path or '').strip()
        if rel_media:
            local = (media_root / rel_media).resolve()
            try:
                if str(local).startswith(str(media_root)) and local.is_file():
                    local.unlink()
            except OSError as e:
                logger.warning(
                    'Retention: failed to delete local backup job=%s path=%s: %s',
                    scheduled_job_id,
                    rel_media,
                    e,
                )

        record.delete()
        deleted += 1

    if deleted:
        logger.info(
            'Retention: pruned %s backup(s) for schedule %s older than %s day(s)',
            deleted,
            scheduled_job_id,
            retention_days,
        )
    return deleted
