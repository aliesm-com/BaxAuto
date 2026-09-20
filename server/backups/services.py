from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from django.conf import settings
from django.utils import timezone

from dbs import restore as dbs_restore
from dbs.base import BackupRestoreError

from db_connections.services import tunneled_connection_params
from storage.models import StorageDestination
from storage.transfer import StorageTransferError, download_backup_file

from .compression import gunzip_to_temp, looks_gzipped
from .models import BackupRecord, RestoreRecord
from .retention import remote_relative_from_media


class UnlinkingFile:
    """File wrapper that deletes the path when closed (streaming temp / purged locals)."""

    def __init__(self, path: Path):
        self._path = Path(path)
        self._fh = self._path.open('rb')

    def read(self, *args, **kwargs):
        return self._fh.read(*args, **kwargs)

    def seek(self, *args, **kwargs):
        return self._fh.seek(*args, **kwargs)

    def tell(self, *args, **kwargs):
        return self._fh.tell(*args, **kwargs)

    def seekable(self):
        return self._fh.seekable()

    def readable(self):
        return True

    def writable(self):
        return False

    def close(self):
        try:
            self._fh.close()
        finally:
            self._path.unlink(missing_ok=True)

    def __iter__(self):
        return iter(self._fh)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


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


def local_backup_available(backup: BackupRecord) -> bool:
    try:
        return resolved_backup_file(backup).is_file()
    except BackupRestoreError:
        return False


def successful_storage_uploads(backup: BackupRecord) -> list[dict]:
    uploads = backup.storage_uploads if isinstance(backup.storage_uploads, list) else []
    out: list[dict] = []
    for entry in uploads:
        if not isinstance(entry, dict) or not entry.get('ok'):
            continue
        dest_id = entry.get('id')
        if not isinstance(dest_id, int):
            continue
        out.append(entry)
    return out


def remote_relative_for_upload(backup: BackupRecord, entry: dict) -> str:
    stored = entry.get('relative')
    if isinstance(stored, str) and stored.strip():
        return stored.strip()
    derived = remote_relative_from_media(backup.relative_media_path)
    if derived:
        return derived
    raise BackupRestoreError('Backup has no remote path recorded for this storage destination.')


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


@contextmanager
def open_backup_artifact(backup: BackupRecord, *, storage_id: int | None = None) -> Iterator[Path]:
    """
    Yield a readable path for ``backup``.

    ``storage_id`` None → local MEDIA file.
    Otherwise download from that storage destination into a temp file (deleted on exit).
    """
    if storage_id is None:
        path = resolved_backup_file(backup)
        if not path.is_file():
            raise BackupRestoreError(f'Backup file missing on disk: {backup.relative_media_path}')
        yield path
        return

    uploads = {u['id']: u for u in successful_storage_uploads(backup)}
    entry = uploads.get(storage_id)
    if entry is None:
        raise BackupRestoreError(
            f'Storage destination #{storage_id} has no successful upload for this backup.',
        )

    try:
        dest = StorageDestination.objects.get(pk=storage_id)
    except StorageDestination.DoesNotExist as e:
        raise BackupRestoreError(f'Storage destination #{storage_id} no longer exists.') from e

    remote_rel = remote_relative_for_upload(backup, entry)
    suffix = Path(backup.download_filename or remote_rel).suffix or '.bin'
    tmp = tempfile.NamedTemporaryFile(prefix=f'bax-backup-{backup.pk}-', suffix=suffix, delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    try:
        try:
            download_backup_file(dest, remote_rel, tmp_path)
        except (StorageTransferError, OSError) as e:
            raise BackupRestoreError(f'Could not download backup from storage: {e}') from e
        yield tmp_path
    finally:
        tmp_path.unlink(missing_ok=True)


def perform_restore(
    *,
    backup: BackupRecord,
    initiated_by: Any,
    restore_kwargs: dict[str, Any],
    storage_id: int | None = None,
) -> RestoreRecord:
    if backup.status != BackupRecord.Status.SUCCESS:
        raise BackupRestoreError('Only successful backups can be restored.')

    opts = dict(restore_kwargs or {})
    if storage_id is not None:
        opts['storage_id'] = storage_id

    connection = backup.connection
    rr = RestoreRecord.objects.create(
        backup=backup,
        connection=connection,
        initiated_by=initiated_by,
        status=RestoreRecord.Status.IN_PROGRESS,
        options=opts,
        engine=backup.engine,
    )

    unpacked: Path | None = None
    try:
        with open_backup_artifact(backup, storage_id=storage_id) as path:
            src = path
            if looks_gzipped(path, bool(backup.compressed)):
                try:
                    unpacked = gunzip_to_temp(path)
                    src = unpacked
                except Exception as e:
                    raise BackupRestoreError(f'Could not decompress gzip backup: {e}') from e

            with tunneled_connection_params(connection) as params:
                dbs_restore(backup.engine, params, src=src, **{k: v for k, v in opts.items() if k != 'storage_id'})
        rr.status = RestoreRecord.Status.SUCCESS
        rr.finished_at = timezone.now()
        rr.save(update_fields=['status', 'finished_at', 'updated_at'])
        from baxconf.alertlog import log_alert

        log_alert(
            f'Restore of backup #{backup.pk} onto “{connection.name}” completed.',
            status='success',
            source='restore',
            connection_id=connection.pk,
            restore_id=rr.pk,
            backup_id=backup.pk,
        )
        return rr
    except Exception as e:
        rr.status = RestoreRecord.Status.FAILED
        rr.error_message = str(e)[:8000]
        rr.finished_at = timezone.now()
        rr.save(update_fields=['status', 'error_message', 'finished_at', 'updated_at'])
        from baxconf.alertlog import log_alert

        log_alert(
            f'Restore of backup #{backup.pk} onto “{connection.name}” failed: {rr.error_message}',
            status='error',
            source='restore',
            error=(rr.error_message or 'restore failed')[:255],
            connection_id=connection.pk,
            restore_id=rr.pk,
            backup_id=backup.pk,
        )
        if isinstance(e, BackupRestoreError):
            raise
        raise BackupRestoreError(str(e)) from e
    finally:
        if unpacked is not None:
            unpacked.unlink(missing_ok=True)
