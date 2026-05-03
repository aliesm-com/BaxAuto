"""Shared helpers and abstract backend for database backup / restore / connection tests."""

from __future__ import annotations

import base64
import os
import shutil
import socket
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class BackupRestoreError(RuntimeError):
    """Raised when backup/restore/test fails or a dependency is missing."""


class DatabaseBackend(ABC):
    """One subclass per engine family; keeps backup/restore/test together."""

    engine: ClassVar[str]

    @abstractmethod
    def test_connection(self, params: Mapping[str, Any]) -> None:
        """Verify reachability and credentials; raise :exc:`BackupRestoreError` on failure."""

    @abstractmethod
    def backup(self, params: Mapping[str, Any], dest: Path, **kwargs: Any) -> Path:
        ...

    @abstractmethod
    def restore(self, params: Mapping[str, Any], src: Path, **kwargs: Any) -> None:
        ...


def require_executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise BackupRestoreError(
            f'Executable "{name}" not found on PATH; install the client tools for this engine.'
        )
    return path


def run_cmd(
    argv: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
) -> None:
    merged = {**os.environ, **dict(env or {})}
    try:
        subprocess.run(
            list(argv),
            check=True,
            env=merged,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or '').strip()
        raise BackupRestoreError(f'Command failed ({e.returncode}): {" ".join(argv)}\n{err}') from e


def run_cmd_text(argv: Sequence[str], *, env: Mapping[str, str] | None = None) -> str:
    merged = {**os.environ, **dict(env or {})}
    try:
        r = subprocess.run(
            list(argv),
            check=True,
            env=merged,
            capture_output=True,
            text=True,
        )
        return (r.stdout or '').strip()
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or '').strip()
        raise BackupRestoreError(f'Command failed ({e.returncode}): {" ".join(argv)}\n{err}') from e


def tcp_probe(host: str, port: int, *, timeout: float = 8.0) -> None:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as e:
        raise BackupRestoreError(f'Cannot reach {host}:{port} ({e}).') from e


def http_request_ok(url: str, *, headers: Mapping[str, str] | None = None, timeout: float = 8.0) -> None:
    req = Request(url, headers=dict(headers or {}))
    try:
        with urlopen(req, timeout=timeout) as resp:
            if resp.status >= 400:
                raise BackupRestoreError(f'HTTP {resp.status} from {url}')
    except HTTPError as e:
        raise BackupRestoreError(f'Management HTTP error {e.code}: {url}') from e
    except URLError as e:
        raise BackupRestoreError(f'HTTP request failed: {url} ({e.reason})') from e


def basic_auth_header(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f'{username}:{password}'.encode()).decode('ascii')
    return {'Authorization': f'Basic {token}'}


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def extras_dict(params: Mapping[str, Any]) -> dict[str, Any]:
    ex = params.get('extra_options')
    return ex if isinstance(ex, dict) else {}
