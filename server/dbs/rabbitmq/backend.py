"""RabbitMQ — management HTTP ``/api/overview`` test; ``/api/definitions`` backup & restore."""

from __future__ import annotations

import ssl
from pathlib import Path
from typing import Any, ClassVar, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dbs.base import (
    BackupRestoreError,
    DatabaseBackend,
    basic_auth_header,
    extras_dict,
    tcp_probe,
)


class Backend(DatabaseBackend):
    engine: ClassVar[str] = 'rabbitmq'

    def _mgmt_url(self, params: Mapping[str, Any], path: str) -> tuple[str, dict[str, str], ssl.SSLContext]:
        host = str(params.get('host') or 'localhost')
        extras = extras_dict(params)
        mgmt_port = int(extras.get('management_port', 15672))
        scheme = 'https' if params.get('use_tls') else 'http'
        user = params.get('username')
        pwd = params.get('password')
        if user is None or str(user).strip() == '':
            raise BackupRestoreError(
                'RabbitMQ management API requires a username (and usually a password).'
            )
        hdr = basic_auth_header(str(user), str(pwd or ''))
        insecure = bool(extras.get('insecure_tls'))
        ctx = ssl._create_unverified_context() if insecure else ssl.create_default_context()
        url = f'{scheme}://{host}:{mgmt_port}{path}'
        return url, hdr, ctx

    def test_connection(self, params: Mapping[str, Any]) -> None:
        host = str(params.get('host') or 'localhost')
        amqp_port = int(params.get('port') or 5672)
        user = params.get('username')
        if user is None or str(user).strip() == '':
            tcp_probe(host, amqp_port)
            return
        url, hdr, ctx = self._mgmt_url(params, '/api/overview')
        try:
            req = Request(url, headers=dict(hdr))
            with urlopen(req, timeout=15, context=ctx) as resp:
                if resp.status >= 400:
                    raise BackupRestoreError(f'Management HTTP {resp.status}: {url}')
        except HTTPError as e:
            raise BackupRestoreError(f'RabbitMQ management HTTP error {e.code}: {url}') from e
        except URLError as e:
            raise BackupRestoreError(f'RabbitMQ management probe failed: {e.reason}') from e

    def backup(self, params: Mapping[str, Any], dest: Path, **kwargs: Any) -> Path:
        dest = Path(dest)
        if dest.suffix.lower() != '.json':
            dest = dest.with_suffix('.json')
        dest.parent.mkdir(parents=True, exist_ok=True)
        url, hdr, ctx = self._mgmt_url(params, '/api/definitions')
        try:
            req = Request(url, headers=dict(hdr))
            with urlopen(req, timeout=600, context=ctx) as resp:
                if resp.status >= 400:
                    raise BackupRestoreError(f'Export definitions failed HTTP {resp.status}')
                body = resp.read()
        except HTTPError as e:
            raise BackupRestoreError(f'Export definitions HTTP {e.code}: {e.reason}') from e
        except URLError as e:
            raise BackupRestoreError(f'Export definitions failed: {e.reason}') from e
        dest.write_bytes(body)
        return dest

    def restore(self, params: Mapping[str, Any], src: Path, **kwargs: Any) -> None:
        src = Path(src)
        if not src.is_file():
            raise BackupRestoreError(f'Backup file not found: {src}')
        url, hdr, ctx = self._mgmt_url(params, '/api/definitions')
        body = src.read_bytes()
        hdr2 = {
            **hdr,
            'Content-Type': 'application/json',
        }
        try:
            req = Request(url, data=body, headers=hdr2, method='POST')
            with urlopen(req, timeout=600, context=ctx) as resp:
                if resp.status >= 400:
                    detail = resp.read().decode('utf-8', errors='replace')[:2000]
                    raise BackupRestoreError(
                        f'Import definitions failed HTTP {resp.status}: {detail}'
                    )
        except HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')[:2000] if e.fp else ''
            raise BackupRestoreError(
                f'Import definitions HTTP {e.code}: {err_body or e.reason}'
            ) from e
        except URLError as e:
            raise BackupRestoreError(f'Import definitions failed: {e.reason}') from e
