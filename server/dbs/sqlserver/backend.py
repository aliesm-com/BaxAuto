"""SQL Server — ``sqlcmd`` connectivity test; logical export/import via ``sqlpackage`` (.bacpac)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, ClassVar, Mapping

from dbs.base import BackupRestoreError, DatabaseBackend, ensure_parent, extras_dict, tcp_probe


class Backend(DatabaseBackend):
    engine: ClassVar[str] = 'sqlserver'

    def test_connection(self, params: Mapping[str, Any]) -> None:
        host = str(params.get('host') or 'localhost')
        extras = extras_dict(params)
        port = int(params.get('port') or extras.get('port') or 1433)

        sqlcmd = shutil.which('sqlcmd')
        db = params.get('database_name')
        user = params.get('username')
        pwd = params.get('password')

        if sqlcmd and db:
            target = f'tcp:{host},{port}'
            cmd = [sqlcmd, '-S', target, '-d', str(db), '-Q', 'SELECT 1', '-b']
            if user:
                cmd.extend(['-U', str(user), '-P', str(pwd or '')])
            else:
                cmd.append('-E')
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise BackupRestoreError(
                    (proc.stderr or proc.stdout or '').strip() or 'sqlcmd failed'
                )
            return

        tcp_probe(host, port)
        if sqlcmd and not db:
            raise BackupRestoreError(
                'sqlcmd is available but database_name is empty; set it for SELECT 1 validation.'
            )

    def _build_sqlpackage_cmd(self, params: Mapping[str, Any], *, export: bool, path: Path) -> list[str]:
        host = str(params.get('host') or 'localhost')
        extras = extras_dict(params)
        port = int(params.get('port') or extras.get('port') or 1433)
        db = params.get('database_name')
        user = params.get('username')
        pwd = params.get('password')

        if not db:
            raise BackupRestoreError('database_name is required for SQL Server backup/restore.')
        if not user:
            raise BackupRestoreError(
                'SQL username/password are required for sqlpackage backup/restore '
                '(integrated Windows auth from this runner is not supported).'
            )

        server = f'{host},{port}'
        if export:
            return [
                'sqlpackage',
                '/Action:Export',
                f'/SourceServerName:{server}',
                f'/SourceDatabaseName:{db}',
                f'/SourceUser:{user}',
                f'/SourcePassword:{pwd or ""}',
                '/Quiet:True',
                f'/TargetFile:{path}',
                '/SourceTrustServerCertificate:True',
            ]
        return [
            'sqlpackage',
            '/Action:Import',
            f'/SourceFile:{path}',
            f'/TargetServerName:{server}',
            f'/TargetDatabaseName:{db}',
            f'/TargetUser:{user}',
            f'/TargetPassword:{pwd or ""}',
            '/Quiet:True',
            '/TargetTrustServerCertificate:True',
        ]

    def backup(self, params: Mapping[str, Any], dest: Path, **kwargs: Any) -> Path:
        if not shutil.which('sqlpackage'):
            raise BackupRestoreError(
                'sqlpackage not found on PATH. Install Microsoft SqlPackage (see server Dockerfile).'
            )
        dest = Path(dest)
        if dest.suffix.lower() != '.bacpac':
            dest = dest.with_suffix('.bacpac')
        ensure_parent(dest)
        cmd = self._build_sqlpackage_cmd(params, export=True, path=dest)
        self._run_sqlpackage(cmd)
        return dest

    def restore(self, params: Mapping[str, Any], src: Path, **kwargs: Any) -> None:
        if not shutil.which('sqlpackage'):
            raise BackupRestoreError(
                'sqlpackage not found on PATH. Install Microsoft SqlPackage (see server Dockerfile).'
            )
        src = Path(src)
        if not src.is_file():
            raise BackupRestoreError(f'Backup file not found: {src}')
        cmd = self._build_sqlpackage_cmd(params, export=False, path=src)
        self._run_sqlpackage(cmd)

    def _run_sqlpackage(self, cmd: list[str]) -> None:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=86400,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise BackupRestoreError('sqlpackage timed out') from e
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or '').strip()
            raise BackupRestoreError(f'sqlpackage failed ({proc.returncode}): {err}')
