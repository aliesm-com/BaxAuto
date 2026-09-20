"""Build ``params`` for ``dbs`` backends and run backup/test against saved connections."""

from __future__ import annotations

import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from django.conf import settings
from django.db import connections
from django.utils import timezone
from django.utils.text import slugify

from backups.compression import gzip_if_requested
from backups.models import BackupRecord
from dbs import backup as dbs_backup
from dbs import test_connection as dbs_test
from dbs.base import BackupRestoreError, extras_dict
from storage.models import StorageDestination
from storage.transfer import StorageTransferError, upload_backup_file

from .models import DatabaseConnection
from .ssh_tunnel import (
    EXTRA_ENGINE_PORTS,
    default_remote_db_port,
    ssh_local_forwards,
)


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


@contextmanager
def tunneled_connection_params(connection: DatabaseConnection) -> Iterator[dict]:
    """
    Yield backend params, opening an SSH local forward when ``ssh_enabled``.

    When tunneling, ``host`` becomes ``127.0.0.1`` and ``port`` the local bind.
    Secondary engine ports (ClickHouse HTTP, RabbitMQ management) are forwarded too.
    """
    params = connection_to_params(connection)
    if not connection.ssh_enabled:
        yield params
        return

    if (params.get('connection_uri') or '').strip():
        raise BackupRestoreError(
            'SSH tunnel cannot be used with a connection URI; use host/port instead.'
        )

    remote_host = (connection.host or '').strip() or '127.0.0.1'
    remote_port = default_remote_db_port(connection.engine, connection.port)
    remotes: list[tuple[str, int]] = [(remote_host, remote_port)]

    extra_key: str | None = None
    extra_remote_port: int | None = None
    if connection.engine in EXTRA_ENGINE_PORTS:
        extra_key, default_extra = EXTRA_ENGINE_PORTS[connection.engine]
        extras = extras_dict(params)
        try:
            extra_remote_port = int(extras.get(extra_key, default_extra))
        except (TypeError, ValueError):
            extra_remote_port = default_extra
        if extra_remote_port != remote_port:
            remotes.append((remote_host, extra_remote_port))

    with ssh_local_forwards(
        ssh_host=(connection.ssh_host or '').strip(),
        ssh_port=int(connection.ssh_port or 22),
        ssh_username=(connection.ssh_username or '').strip(),
        ssh_password=connection.ssh_password or '',
        ssh_private_key=connection.ssh_private_key or '',
        ssh_private_key_passphrase=connection.ssh_private_key_passphrase or '',
        host_key_fingerprint=connection.ssh_host_key_fingerprint or '',
        remotes=remotes,
    ) as local_ports:
        params = dict(params)
        params['host'] = '127.0.0.1'
        params['port'] = local_ports[0]
        params['connection_uri'] = ''
        if extra_key and len(local_ports) > 1:
            extras = dict(params.get('extra_options') or {})
            extras[extra_key] = local_ports[1]
            params['extra_options'] = extras
        yield params


def _backup_run_subdir(*, trigger: str, schedule_job_id: int | None, schedule_job_name: str) -> str:
    """Folder under the connection slug: ``manual`` or ``{id}-{schedule-slug}``."""
    if trigger == BackupRecord.Trigger.SCHEDULED and schedule_job_id:
        slug = slugify(schedule_job_name or '')[:60] or 'schedule'
        return f'{int(schedule_job_id)}-{slug}'
    return 'manual'


def _fanout_backup_to_storages(user_id: int, local_path: Path, remote_relative: str) -> list[dict]:
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
            entry['remote'] = upload_backup_file(dest, local_path, remote_relative)
            entry['relative'] = remote_relative
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
    schedule_job_id: int | None = None,
    schedule_job_name: str = '',
) -> tuple[Path, str]:
    """
    Run logical backup for this saved connection.

    Layout under ``MEDIA_ROOT`` (and under each storage ``remote_path``)::

        db_exports/<user_id>/<connection-slug>/manual/<file>
        db_exports/<user_id>/<connection-slug>/<job-id>-<schedule-slug>/<file>

    After a successful dump, the file is copied to every ``StorageDestination`` belonging
    to the connection owner. ``compress`` gzip-encodes the artifact first (skipped for
    formats that are already packed, e.g. ``.zip``).

    Logs a :class:`backups.models.BackupRecord` row (success or failure).

    ``trigger`` defaults to manual API when omitted.
    """
    if trigger is None:
        trigger = BackupRecord.Trigger.MANUAL

    actor = initiated_by if initiated_by is not None else connection.user

    engine = connection.engine

    db_slug = slugify(connection.name)[:80] or f'connection-{connection.pk}'
    run_subdir = _backup_run_subdir(
        trigger=trigger,
        schedule_job_id=schedule_job_id,
        schedule_job_name=schedule_job_name,
    )
    export_root = Path(settings.MEDIA_ROOT) / 'db_exports' / str(connection.user_id) / db_slug / run_subdir
    export_root.mkdir(parents=True, exist_ok=True)
    stamp = timezone.localtime().strftime('%Y%m%d_%H%M%S')
    file_slug = db_slug

    record = BackupRecord.objects.create(
        connection=connection,
        initiated_by=actor,
        trigger=trigger,
        status=BackupRecord.Status.IN_PROGRESS,
        engine=engine,
        scheduled_job_id=(
            schedule_job_id if trigger == BackupRecord.Trigger.SCHEDULED and schedule_job_id else None
        ),
    )
    record_id = record.pk
    connections.close_all()

    media_root = Path(settings.MEDIA_ROOT).resolve()

    try:
        with tunneled_connection_params(connection) as params:
            if engine == DatabaseConnection.Engine.MONGODB:
                job_dir = export_root / f'{file_slug}_{stamp}_mongo_work'
                job_dir.mkdir(parents=True, exist_ok=True)
                dump_root = dbs_backup(engine, params, dest=job_dir)
                archive_base = export_root / f'{file_slug}_{stamp}'
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
                out_path = export_root / f'{file_slug}_{stamp}{ext}'
                dbs_backup(engine, params, dest=out_path)
                path, filename = out_path, out_path.name

        path = gzip_if_requested(path, compress)
        filename = path.name
        was_gzipped = path.suffix.lower() == '.gz'
        remote_relative = f'{db_slug}/{run_subdir}/{filename}'
        storage_uploads = _fanout_backup_to_storages(connection.user_id, path, remote_relative)

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
            f'{kind} of “{connection.name}” completed ({remote_relative}, {record.size_bytes} bytes{storage_note}).',
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
    result = probe_saved_connection(connection)
    if result.get('ok'):
        return
    ssh = result.get('ssh') or {}
    db = result.get('database') or {}
    if ssh.get('enabled') and ssh.get('ok') is False:
        raise BackupRestoreError(f"SSH tunnel failed: {ssh.get('detail') or 'unknown error'}")
    raise BackupRestoreError(f"Database probe failed: {db.get('detail') or 'unknown error'}")


def probe_saved_connection(connection: DatabaseConnection) -> dict:
    """
    Probe SSH (when enabled) and the database separately.

    Returns a JSON-serializable dict::

        {
          "ok": bool,
          "ssh": {"enabled": bool, "ok": bool|None, "detail": str},
          "database": {"ok": bool|None, "detail": str},
        }
    """
    engine_label = connection.get_engine_display()
    result: dict = {
        'ok': False,
        'ssh': {
            'enabled': bool(connection.ssh_enabled),
            'ok': None,
            'detail': '',
        },
        'database': {
            'ok': None,
            'detail': '',
        },
    }

    if not connection.ssh_enabled:
        result['ssh'] = {
            'enabled': False,
            'ok': True,
            'detail': 'SSH tunnel is off; testing a direct database connection.',
        }
        try:
            dbs_test(connection.engine, connection_to_params(connection))
        except Exception as e:
            result['database'] = {
                'ok': False,
                'detail': str(e)[:2000],
            }
            return result
        result['database'] = {
            'ok': True,
            'detail': f'{engine_label} accepted the connection.',
        }
        result['ok'] = True
        return result

    try:
        with tunneled_connection_params(connection) as params:
            local_port = params.get('port')
            result['ssh'] = {
                'enabled': True,
                'ok': True,
                'detail': (
                    f'SSH tunnel to {connection.ssh_host}:{connection.ssh_port or 22} OK '
                    f'(local 127.0.0.1:{local_port} → '
                    f'{(connection.host or "").strip() or "127.0.0.1"}:'
                    f'{default_remote_db_port(connection.engine, connection.port)}).'
                ),
            }
            try:
                dbs_test(connection.engine, params)
            except Exception as e:
                result['database'] = {
                    'ok': False,
                    'detail': str(e)[:2000],
                }
                return result
            result['database'] = {
                'ok': True,
                'detail': f'{engine_label} accepted the connection through the tunnel.',
            }
            result['ok'] = True
            return result
    except Exception as e:
        result['ssh'] = {
            'enabled': True,
            'ok': False,
            'detail': str(e)[:2000],
        }
        result['database'] = {
            'ok': None,
            'detail': 'Skipped because the SSH tunnel could not be established.',
        }
        return result
