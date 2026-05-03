"""MySQL — mysqldump/mysql + ``SELECT 1`` connection test."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, ClassVar, Mapping

from dbs.base import BackupRestoreError, DatabaseBackend, ensure_parent, require_executable


class Backend(DatabaseBackend):
    engine: ClassVar[str] = 'mysql'

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
        client = require_executable('mysql')
        cmd = [client, *self._conn_args(params), '-e', 'SELECT 1']
        run_cmd_mysql(cmd)

    def backup(self, params: Mapping[str, Any], dest: Path, **kwargs: Any) -> Path:
        dest = Path(dest)
        ensure_parent(dest)
        dump = require_executable('mysqldump')
        db = params.get('database_name')
        if not db:
            raise BackupRestoreError('database_name is required for MySQL backup.')
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
                f'mysqldump failed ({proc.returncode}): '
                f'{proc.stderr.decode(errors="replace")}'
            )
        return dest

    def restore(self, params: Mapping[str, Any], src: Path, **kwargs: Any) -> None:
        src = Path(src)
        if not src.is_file():
            raise BackupRestoreError(f'Backup file not found: {src}')
        db = params.get('database_name')
        if not db:
            raise BackupRestoreError('database_name is required for MySQL restore.')
        client = require_executable('mysql')
        cmd = [client, *self._conn_args(params), str(db)]
        with src.open('rb') as fh:
            proc = subprocess.run(cmd, stdin=fh, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise BackupRestoreError(
                f'mysql restore failed ({proc.returncode}): '
                f'{proc.stderr.decode(errors="replace")}'
            )


def run_cmd_mysql(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise BackupRestoreError(proc.stderr.decode(errors='replace') or 'mysql command failed')
