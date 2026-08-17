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

    def _sslmode(self, params: Mapping[str, Any]) -> str:
        # libpq default is ``prefer`` (try TLS first). Servers without SSL often
        # drop that handshake, which pg_dump reports as "server closed the connection".
        return 'require' if params.get('use_tls') else 'disable'

    def _pg_env(self, password: str | None, params: Mapping[str, Any]) -> dict[str, str]:
        env: dict[str, str] = {
            'PGSSLMODE': self._sslmode(params),
            # Remote COPY of large tables can idle long enough for NAT/firewalls to drop the socket.
            'PGOPTIONS': '-c statement_timeout=0 -c idle_in_transaction_session_timeout=0',
            'PGCONNECT_TIMEOUT': '60',
        }
        if password:
            env['PGPASSWORD'] = password
        return env

    def _connection_args(self, params: Mapping[str, Any]) -> list[str]:
        host = params.get('host') or 'localhost'
        port = params.get('port') or 5432
        user = params.get('username') or os.environ.get('USER', 'postgres')
        db = params.get('database_name')
        if not db:
            raise BackupRestoreError('database_name is required for PostgreSQL.')
        sslmode = self._sslmode(params)
        conninfo = (
            f'host={host} port={port} dbname={db} user={user} sslmode={sslmode} '
            'keepalives=1 keepalives_idle=30 keepalives_interval=10 keepalives_count=5 '
            'connect_timeout=60'
        )
        return ['-d', conninfo]

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
        kw['sslmode'] = self._sslmode(params)
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
        attempts = 3
        last_err: BackupRestoreError | None = None
        for i in range(attempts):
            if dest.exists():
                dest.unlink()
            try:
                run_cmd(cmd, env=self._pg_env(pwd, params))
                return dest
            except BackupRestoreError as e:
                last_err = e
                msg = str(e).lower()
                transient = (
                    'server closed the connection' in msg
                    or 'pqgetcopydata' in msg
                    or 'connection reset' in msg
                    or 'timeout' in msg
                )
                if not transient or i == attempts - 1:
                    raise
        raise last_err or BackupRestoreError('pg_dump failed.')

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
        # UI flags (drop / flush) map to --clean; extra engine-specific keys are ignored.
        do_clean = bool(kwargs.get('drop', clean) or kwargs.get('flush_before_restore', False) or clean)
        cmd = [pg_restore, *self._connection_args(params)]
        if do_clean:
            cmd.extend(['--clean', '--if-exists'])
        cmd.extend(['--no-owner', '--no-acl', '-v', str(src)])
        run_cmd(cmd, env=self._pg_env(pwd, params))
