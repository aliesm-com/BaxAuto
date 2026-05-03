"""MongoDB — mongodump/mongorestore + ping via ``mongosh``/``mongo`` when available."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, ClassVar, Mapping

from dbs.base import BackupRestoreError, DatabaseBackend, extras_dict, require_executable, run_cmd, tcp_probe


class Backend(DatabaseBackend):
    engine: ClassVar[str] = 'mongodb'

    def test_connection(self, params: Mapping[str, Any]) -> None:
        uri = (params.get('connection_uri') or '').strip()
        host = str(params.get('host') or 'localhost')
        port = int(params.get('port') or 27017)
        shell = shutil.which('mongosh') or shutil.which('mongo')

        if shell:
            if uri:
                cmd = [shell, uri, '--quiet', '--eval', 'db.runCommand({ping:1})']
            else:
                cmd = [
                    shell,
                    '--host',
                    host,
                    '--port',
                    str(port),
                    '--quiet',
                    '--eval',
                    'db.runCommand({ping:1})',
                ]
                user = params.get('username')
                pwd = params.get('password')
                if user:
                    cmd.extend(['--username', str(user)])
                if pwd:
                    cmd.extend(['--password', str(pwd)])
                ex = extras_dict(params)
                auth_db = ex.get('authSource') or ex.get('authenticationDatabase')
                if auth_db:
                    cmd.extend(['--authenticationDatabase', str(auth_db)])
                db = params.get('database_name')
                if db:
                    cmd.extend(['--db', str(db)])
            self._run_shell(cmd)
            return

        tcp_probe(host, port)

    def _run_shell(self, cmd: list[str]) -> None:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise BackupRestoreError(
                (proc.stderr or proc.stdout or '').strip() or 'Mongo shell ping failed'
            )

    def backup(self, params: Mapping[str, Any], dest: Path, **kwargs: Any) -> Path:
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        dump = require_executable('mongodump')
        uri = (params.get('connection_uri') or '').strip()
        extras = extras_dict(params)

        if uri:
            cmd = [dump, '--uri', uri, '--out', str(dest)]
        else:
            host = params.get('host') or 'localhost'
            port = params.get('port') or 27017
            db = params.get('database_name')
            cmd = [dump, '--host', str(host), '--port', str(port), '--out', str(dest)]
            user = params.get('username')
            pwd = params.get('password')
            if user:
                cmd.extend(['--username', str(user)])
            if pwd:
                cmd.extend(['--password', str(pwd)])
            auth_db = extras.get('authSource') or extras.get('authenticationDatabase')
            if auth_db:
                cmd.extend(['--authenticationDatabase', str(auth_db)])
            if db:
                cmd.extend(['--db', str(db)])

        run_cmd(cmd)
        return dest

    def restore(
        self,
        params: Mapping[str, Any],
        src: Path,
        *,
        drop: bool = False,
        **kwargs: Any,
    ) -> None:
        src = Path(src)
        if not src.exists():
            raise BackupRestoreError(f'Backup path not found: {src}')
        tool = require_executable('mongorestore')
        uri = (params.get('connection_uri') or '').strip()
        extras = extras_dict(params)

        if uri:
            cmd: list[str] = [tool, '--uri', uri]
        else:
            host = params.get('host') or 'localhost'
            port = params.get('port') or 27017
            cmd = [tool, '--host', str(host), '--port', str(port)]
            user = params.get('username')
            pwd = params.get('password')
            if user:
                cmd.extend(['--username', str(user)])
            if pwd:
                cmd.extend(['--password', str(pwd)])
            auth_db = extras.get('authSource') or extras.get('authenticationDatabase')
            if auth_db:
                cmd.extend(['--authenticationDatabase', str(auth_db)])
            db = params.get('database_name')
            if db:
                cmd.extend(['--db', str(db)])

        if drop:
            cmd.append('--drop')
        cmd.append(str(src))

        run_cmd(cmd)
