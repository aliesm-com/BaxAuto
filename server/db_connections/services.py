"""Build ``params`` for ``dbs`` backends and run backup/test against saved connections."""

from __future__ import annotations

import shutil
from pathlib import Path

from django.conf import settings
from django.db import connections
from django.utils import timezone
from django.utils.text import slugify

from backups.compression import gzip_if_requested
from backups.models import BackupRecord
from dbs import backup as dbs_backup
from dbs import test_connection as dbs_test
from storage.models import StorageDestination
from storage.transfer import StorageTransferError, upload_backup_file

from .models import DatabaseConnection


def connection_to_params(connection: DatabaseConnection) -> dict:
    """Map model fields to the dict expected by ``dbs`` backends."""
    extra = dict(connection.extra_options or {})
    params = {
        'host': (connection.host or '').strip(),
        'port': connection.port,
        'database_name': (connection.database_name or '').strip(),
        'username': (connection.username or '').strip(),
        'password': connection.password or '',
        'connection_uri': (connection.connection_uri or '').strip(),
        'use_tls': connection.use_tls,
        'extra_options': extra,
    }
    if connection.engine == DatabaseConnection.Engine.RABBITMQ:
        extra.setdefault('virtual_host', connection.virtual_host or '/')
    return params


def _fanout_backup_to_storages(user_id: int, local_path: Path, filename: str) -> list[dict]:
    """Copy the dump to every storage destination owned by ``user_id``."""
    results: list[dict] = []
    dests = StorageDestination.objects.filter(user_id=user_id).order_by('id')
    for dest in dests:
        entry: dict = {
            'id': dest.pk,
            'name': dest.name,
            'kind': dest.kind,
            'ok': False,
        }
        try:
            entry['remote'] = upload_backup_file(dest, local_path, filename)
            entry['ok'] = True
        except (StorageTransferError, OSError) as e:
            entry['error'] = str(e)[:800]
        results.append(entry)
    return results


def perform_backup(
    connection: DatabaseConnection,
    *,
    trigger: str | None = None,
    initiated_by=None,
    compress: bool = False,
) -> tuple[Path, str]:
    """
    Run logical backup for this saved connection; write under ``MEDIA_ROOT/db_exports/<user_id>/``.

    After a successful dump, the file is copied to every ``StorageDestination`` belonging
    to the connection owner. ``compress`` gzip-encodes the artifact first (skipped for
    formats that are already packed, e.g. ``.zip``).

    Logs a :class:`backups.models.BackupRecord` row (success or failure).

    ``trigger`` defaults to manual API when omitted.
    """
    if trigger is None:
        trigger = BackupRecord.Trigger.MANUAL

    actor = initiated_by if initiated_by is not None else connection.user

    params = connection_to_params(connection)
    engine = connection.engine

    export_root = Path(settings.MEDIA_ROOT) / 'db_exports' / str(connection.user_id)
    export_root.mkdir(parents=True, exist_ok=True)
    stamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    slug = slugify(connection.name)[:80] or 'connection'

    record = BackupRecord.objects.create(
        connection=connection,
        initiated_by=actor,
        trigger=trigger,
        status=BackupRecord.Status.IN_PROGRESS,
        engine=engine,
    )
    record_id = record.pk
    connections.close_all()

    media_root = Path(settings.MEDIA_ROOT).resolve()

    try:
        if engine == DatabaseConnection.Engine.MONGODB:
            job_dir = export_root / f'{slug}_{stamp}_mongo_work'
            job_dir.mkdir(parents=True, exist_ok=True)
            dump_root = dbs_backup(engine, params, dest=job_dir)
            archive_base = export_root / f'{slug}_{stamp}'
            shutil.make_archive(str(archive_base), 'zip', root_dir=str(dump_root))
            archive_path = Path(str(archive_base) + '.zip')
            shutil.rmtree(job_dir, ignore_errors=True)
            path, filename = archive_path, archive_path.name
        else:
            extensions = {
                DatabaseConnection.Engine.POSTGRESQL: '.dump',
                DatabaseConnection.Engine.MYSQL: '.sql',
                DatabaseConnection.Engine.MARIADB: '.sql',
                DatabaseConnection.Engine.REDIS: '.rdb',
                DatabaseConnection.Engine.SQLSERVER: '.bacpac',
                DatabaseConnection.Engine.CLICKHOUSE: '.zip',
                DatabaseConnection.Engine.RABBITMQ: '.json',
            }
            ext = extensions.get(engine, '.bin')
            out_path = export_root / f'{slug}_{stamp}{ext}'
            dbs_backup(engine, params, dest=out_path)
            path, filename = out_path, out_path.name

        path = gzip_if_requested(path, compress)
        filename = path.name
        was_gzipped = path.suffix.lower() == '.gz'
        storage_uploads = _fanout_backup_to_storages(connection.user_id, path, filename)

        abs_path = path.resolve()
        rel = abs_path.relative_to(media_root)
        record = BackupRecord.objects.get(pk=record_id)
        record.status = BackupRecord.Status.SUCCESS
        record.relative_media_path = rel.as_posix()
        record.download_filename = filename
        record.size_bytes = path.stat().st_size
        record.compressed = was_gzipped
        record.storage_uploads = storage_uploads
        record.finished_at = timezone.now()
        record.save(
            update_fields=[
                'status',
                'relative_media_path',
                'download_filename',
                'size_bytes',
                'compressed',
                'storage_uploads',
                'finished_at',
                'updated_at',
            ]
        )
        from baxconf.alertlog import log_alert

        kind = 'Scheduled backup' if trigger == BackupRecord.Trigger.SCHEDULED else 'Backup'
        failed_uploads = [u for u in storage_uploads if not u.get('ok')]
        ok_uploads = len(storage_uploads) - len(failed_uploads)
        storage_note = ''
        if storage_uploads:
            storage_note = f'; uploaded to {ok_uploads}/{len(storage_uploads)} storage destination(s)'
        log_alert(
            f'{kind} of “{connection.name}” completed ({filename}, {record.size_bytes} bytes{storage_note}).',
            status='success',
            source='backup',
            connection_id=connection.pk,
            backup_id=record.pk,
        )
        if failed_uploads:
            names = ', '.join(str(u.get('name') or u.get('id')) for u in failed_uploads)
            log_alert(
                f'Backup of “{connection.name}” could not be copied to: {names}.',
                status='warning',
                source='backup',
                connection_id=connection.pk,
                backup_id=record.pk,
            )
        return path, filename
    except Exception as e:
        record = BackupRecord.objects.get(pk=record_id)
        record.status = BackupRecord.Status.FAILED
        record.error_message = str(e)[:8000]
        record.finished_at = timezone.now()
        record.save(update_fields=['status', 'error_message', 'finished_at', 'updated_at'])
        from baxconf.alertlog import log_alert

        kind = 'Scheduled backup' if trigger == BackupRecord.Trigger.SCHEDULED else 'Backup'
        log_alert(
            f'{kind} of “{connection.name}” failed: {record.error_message}',
            status='error',
            source='backup',
            connection_id=connection.pk,
            backup_id=record_id,
        )
        raise


def test_saved_connection(connection: DatabaseConnection) -> None:
    """Raise :exc:`BackupRestoreError` if the probe fails."""
    dbs_test(connection.engine, connection_to_params(connection))
