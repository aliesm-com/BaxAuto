"""Redis — RDB snapshot via ``redis-cli --rdb``; restore via ``rdb -c protocol`` piped to ``redis-cli --pipe``."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, ClassVar, Mapping

from dbs.base import (
    BackupRestoreError,
    DatabaseBackend,
    ensure_parent,
    require_executable,
    run_cmd,
    run_cmd_text,
    tcp_probe,
)


class Backend(DatabaseBackend):
    engine: ClassVar[str] = 'redis'

    def _rdb_protocol_argv(self, params: Mapping[str, Any], src: Path) -> list[str]:
        """Args to emit RESP ``protocol`` stream from an RDB file (``rdb`` CLI or ``python -m``)."""
        rdb_exe = shutil.which('rdb')
        if rdb_exe:
            cmd: list[str] = [rdb_exe, '-c', 'protocol']
        else:
            cmd = [sys.executable, '-m', 'rdbtools.cli.rdb', '-c', 'protocol']
        db_idx = (params.get('database_name') or '').strip()
        if db_idx.isdigit():
            cmd.extend(['-n', db_idx])
        cmd.append(str(src))
        return cmd

    def _cli_prefix(self, params: Mapping[str, Any]) -> list[str]:
        host = params.get('host') or '127.0.0.1'
        port = params.get('port') or 6379
        pwd = params.get('password')
        db_idx = (params.get('database_name') or '').strip()
        cli = require_executable('redis-cli')
        cmd = [cli, '-h', str(host), '-p', str(port)]
        if pwd:
            cmd.extend(['-a', str(pwd)])
        if db_idx.isdigit():
            cmd.extend(['-n', db_idx])
        return cmd

    def test_connection(self, params: Mapping[str, Any]) -> None:
        host = str(params.get('host') or '127.0.0.1')
        port = int(params.get('port') or 6379)
        if not shutil.which('redis-cli'):
            tcp_probe(host, port)
            return
        out = run_cmd_text(self._cli_prefix(params) + ['PING'])
        if 'PONG' not in out.upper():
            raise BackupRestoreError(f'Unexpected PING reply: {out!r}')

    def backup(self, params: Mapping[str, Any], dest: Path, **kwargs: Any) -> Path:
        dest = Path(dest)
        ensure_parent(dest)
        cmd = self._cli_prefix(params) + ['--rdb', str(dest)]
        run_cmd(cmd)
        return dest

    def restore(
        self,
        params: Mapping[str, Any],
        src: Path,
        *,
        flush_before_restore: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Replay RDB contents into the **currently selected logical DB** using RESP from
        PyPI ``rdbtools`` (``rdb -c protocol`` or ``python -m rdbtools.cli.rdb``).
        Optional ``flush_before_restore`` runs ``FLUSHDB`` first (destructive).
        """
        src = Path(src)
        if not src.is_file():
            raise BackupRestoreError(f'Backup file not found: {src}')
        if not shutil.which('rdb') and importlib.util.find_spec('rdbtools') is None:
            raise BackupRestoreError(
                'Redis RDB restore needs PyPI package ``rdbtools`` (see requirements.txt), '
                'or the ``rdb`` CLI on PATH.'
            )

        argv = self._rdb_protocol_argv(params, src)

        if flush_before_restore:
            run_cmd(self._cli_prefix(params) + ['FLUSHDB'])

        proto = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert proto.stdout is not None
        pipe = subprocess.run(
            self._cli_prefix(params) + ['--pipe'],
            stdin=proto.stdout,
            capture_output=True,
        )
        proto.stdout.close()
        stderr_rdb = proto.stderr.read().decode(errors='replace') if proto.stderr else ''
        proto.wait(timeout=86400)
        if proto.returncode != 0:
            raise BackupRestoreError(f'rdb protocol generation failed: {stderr_rdb}'.strip())
        if pipe.returncode != 0:
            err = (pipe.stderr or pipe.stdout or b'').decode(errors='replace')
            raise BackupRestoreError(f'redis-cli --pipe failed: {err}'.strip())
