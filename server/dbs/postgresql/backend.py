"""PostgreSQL — backup/restore + connection test (``psycopg2`` when available)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, ClassVar, Mapping

try:
    import psycopg2
except ImportError:
    psycopg2 = None  # type: ignore[misc, assignment]

from dbs.base import (
    BackupRestoreError,
    DatabaseBackend,
    ensure_parent,
    require_executable,
    run_cmd,
    tcp_probe,
)


class Backend(DatabaseBackend):
    engine: ClassVar[str] = 'postgresql'

    def _pg_env(self, password: str | None, params: Mapping[str, Any]) -> dict[str, str]:
        env: dict[str, str] = {}
        if password:
            env['PGPASSWORD'] = password
        if params.get('use_tls'):
            env.setdefault('PGSSLMODE', 'require')
        return env

    def _connection_args(self, params: Mapping[str, Any]) -> list[str]:
        host = params.get('host') or 'localhost'
        port = params.get('port') or 5432
        user = params.get('username') or os.environ.get('USER', 'postgres')
        db = params.get('database_name')
        if not db:
            raise BackupRestoreError('database_name is required for PostgreSQL.')
        return ['-h', str(host), '-p', str(port), '-U', str(user), '-d', str(db)]

    def test_connection(self, params: Mapping[str, Any]) -> None:
        host = str(params.get('host') or 'localhost')
        port = int(params.get('port') or 5432)
        db = params.get('database_name')
        if not db:
            raise BackupRestoreError('database_name is required to test PostgreSQL.')

        if psycopg2 is None:
            ready = shutil.which('pg_isready')
            if ready:
                pwd = (params.get('password') or '') or None
                argv = [ready, '-h', host, '-p', str(port), '-d', str(db)]
                run_cmd(argv, env=self._pg_env(pwd, params))
                return
            tcp_probe(host, port)
            raise BackupRestoreError(
                'Install psycopg2-binary (recommended) or PostgreSQL client ``pg_isready`` '
                'for a real connection test.'
            ) from None

        kw: dict[str, Any] = dict(
            host=host,
            port=port,
            dbname=str(db),
            user=params.get('username') or os.environ.get('USER', 'postgres'),
            password=params.get('password') or None,
            connect_timeout=8,
        )
        if params.get('use_tls'):
            kw['sslmode'] = 'require'
        try:
            conn = psycopg2.connect(**kw)
            conn.close()
        except Exception as e:
            raise BackupRestoreError(f'PostgreSQL connection failed: {e}') from e

    def backup(self, params: Mapping[str, Any], dest: Path, **kwargs: Any) -> Path:
        dest = Path(dest)
        ensure_parent(dest)
        pwd = (params.get('password') or '') or None
        pg_dump = require_executable('pg_dump')
        cmd = [
            pg_dump,
            *self._connection_args(params),
            '-Fc',
            '-f',
            str(dest),
        ]
        run_cmd(cmd, env=self._pg_env(pwd, params))
        return dest

    def restore(
        self,
        params: Mapping[str, Any],
        src: Path,
        *,
        clean: bool = True,
        **kwargs: Any,
    ) -> None:
        src = Path(src)
        if not src.is_file():
            raise BackupRestoreError(f'Backup file not found: {src}')
        pwd = (params.get('password') or '') or None
        pg_restore = require_executable('pg_restore')
        cmd = [pg_restore, *self._connection_args(params)]
        if clean:
            cmd.extend(['--clean', '--if-exists'])
        cmd.extend(['-v', str(src)])
        run_cmd(cmd, env=self._pg_env(pwd, params))
