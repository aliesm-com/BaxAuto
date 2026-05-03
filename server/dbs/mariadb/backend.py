"""MariaDB — mariadb-dump / mariadb clients + ``SELECT 1`` test."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, ClassVar, Mapping

from dbs.base import BackupRestoreError, DatabaseBackend, ensure_parent

from dbs.mysql.backend import run_cmd_mysql


class Backend(DatabaseBackend):
    engine: ClassVar[str] = 'mariadb'

    def _dump_executable(self) -> str:
        return shutil.which('mariadb-dump') or shutil.which('mysqldump') or ''

    def _client_executable(self) -> str:
        return shutil.which('mariadb') or shutil.which('mysql') or ''

    def _conn_args(self, params: Mapping[str, Any]) -> list[str]:
        host = params.get('host') or 'localhost'
        port = params.get('port') or 3306
        user = params.get('username') or 'root'
        args: list[str] = ['-h', str(host), '-P', str(port), '-u', str(user)]
        pwd = params.get('password')
        if pwd:
            args.append(f'-p{pwd}')
        return args

    def test_connection(self, params: Mapping[str, Any]) -> None:
        client = self._client_executable()
        if not client:
            raise BackupRestoreError('Neither mariadb nor mysql client found on PATH.')
        cmd = [client, *self._conn_args(params), '-e', 'SELECT 1']
        run_cmd_mysql(cmd)

    def backup(self, params: Mapping[str, Any], dest: Path, **kwargs: Any) -> Path:
        dump = self._dump_executable()
        if not dump:
            raise BackupRestoreError('Neither mariadb-dump nor mysqldump found on PATH.')
        db = params.get('database_name')
        if not db:
            raise BackupRestoreError('database_name is required for MariaDB backup.')
        dest = Path(dest)
        ensure_parent(dest)
        cmd = [
            dump,
            *self._conn_args(params),
            '--single-transaction',
            '--routines',
            '--events',
            str(db),
        ]
        with dest.open('wb') as out:
            proc = subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            dest.unlink(missing_ok=True)
            raise BackupRestoreError(
                f'dump failed ({proc.returncode}): {proc.stderr.decode(errors="replace")}'
            )
        return dest

    def restore(self, params: Mapping[str, Any], src: Path, **kwargs: Any) -> None:
        client = self._client_executable()
        if not client:
            raise BackupRestoreError('Neither mariadb nor mysql client found on PATH.')
        db = params.get('database_name')
        if not db:
            raise BackupRestoreError('database_name is required for MariaDB restore.')
        src = Path(src)
        if not src.is_file():
            raise BackupRestoreError(f'Backup file not found: {src}')
        cmd = [client, *self._conn_args(params), str(db)]
        with src.open('rb') as fh:
            proc = subprocess.run(cmd, stdin=fh, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise BackupRestoreError(
                f'restore failed ({proc.returncode}): {proc.stderr.decode(errors="replace")}'
            )
