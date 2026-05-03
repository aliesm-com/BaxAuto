"""ClickHouse — HTTP ``/ping`` test; ZIP backup (DDL stubs + ``CSVWithNames`` per table); restore via HTTP INSERT."""

from __future__ import annotations

import re
import shutil
import ssl
import zipfile
from pathlib import Path
from typing import Any, ClassVar, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from dbs.base import BackupRestoreError, DatabaseBackend, basic_auth_header, extras_dict


_SAFE_IDENT = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


class Backend(DatabaseBackend):
    engine: ClassVar[str] = 'clickhouse'

    def _http_base(self, params: Mapping[str, Any]) -> tuple[str, dict[str, str], ssl.SSLContext]:
        host = str(params.get('host') or 'localhost')
        extras = extras_dict(params)
        http_port = int(extras.get('http_port', 8123))
        scheme = 'https' if params.get('use_tls') else 'http'
        base = f'{scheme}://{host}:{http_port}'
        user = params.get('username')
        pwd = params.get('password')
        headers: dict[str, str] = {}
        if user:
            headers = basic_auth_header(str(user), str(pwd or ''))
        insecure = bool(extras.get('insecure_tls'))
        ctx = ssl._create_unverified_context() if insecure else ssl.create_default_context()
        return base, headers, ctx

    def _get(self, url: str, headers: Mapping[str, str], ctx: ssl.SSLContext, timeout: float = 600):
        req = Request(url, headers=dict(headers))
        return urlopen(req, timeout=timeout, context=ctx)

    def _post_sql(
        self,
        base: str,
        query: str,
        headers: Mapping[str, str],
        ctx: ssl.SSLContext,
        *,
        timeout: float = 600,
    ):
        url = base.rstrip('/') + '/'
        hdr = {**dict(headers), 'Content-Type': 'text/plain; charset=utf-8'}
        req = Request(url, data=query.encode('utf-8'), headers=hdr, method='POST')
        return urlopen(req, timeout=timeout, context=ctx)

    def _post_ddl(self, base: str, ddl: str, headers: Mapping[str, str], ctx: ssl.SSLContext) -> None:
        url = base.rstrip('/') + '/'
        hdr = {**dict(headers), 'Content-Type': 'text/plain; charset=utf-8'}
        req = Request(url, data=ddl.strip().encode('utf-8'), headers=hdr, method='POST')
        try:
            with urlopen(req, timeout=600, context=ctx) as resp:
                if resp.status >= 400:
                    raise BackupRestoreError(
                        f'DDL execution HTTP {resp.status}: {resp.read()[:500]!r}'
                    )
        except HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')[:2000] if e.fp else ''
            raise BackupRestoreError(f'DDL HTTP {e.code}: {body}') from e

    def _post_insert_csv(
        self,
        base: str,
        db: str,
        table: str,
        csv_body: bytes,
        headers: Mapping[str, str],
        ctx: ssl.SSLContext,
    ) -> None:
        q = f'INSERT INTO `{db}`.`{table}` FORMAT CSVWithNames'
        url = base.rstrip('/') + '/?query=' + quote_plus(q)
        hdr = {**dict(headers), 'Content-Type': 'text/csv; charset=utf-8'}
        req = Request(url, data=csv_body, headers=hdr, method='POST')
        try:
            with urlopen(req, timeout=86400, context=ctx) as resp:
                if resp.status >= 400:
                    raise BackupRestoreError(
                        f'INSERT {table!r} HTTP {resp.status}: {resp.read()[:500]!r}'
                    )
        except HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')[:2000] if e.fp else ''
            raise BackupRestoreError(f'INSERT {table!r} HTTP {e.code}: {body}') from e

    def test_connection(self, params: Mapping[str, Any]) -> None:
        base, headers, ctx = self._http_base(params)
        url = f'{base}/ping'
        try:
            with self._get(url, headers, ctx, timeout=15) as resp:
                if resp.status >= 400:
                    raise BackupRestoreError(f'HTTP {resp.status} from {url}')
        except HTTPError as e:
            raise BackupRestoreError(f'ClickHouse HTTP error {e.code}: {url}') from e
        except URLError as e:
            raise BackupRestoreError(f'ClickHouse ping failed: {e.reason}') from e

    def _list_tables(self, params: Mapping[str, Any], database: str) -> list[str]:
        if not _SAFE_IDENT.match(database):
            raise BackupRestoreError(
                'database_name must be a simple identifier (letters, digits, underscore).'
            )
        base, headers, ctx = self._http_base(params)
        q = (
            f"SELECT name FROM system.tables WHERE database = '{database}' "
            'AND is_temporary = 0 ORDER BY name FORMAT TabSeparated'
        )
        try:
            with self._post_sql(base, q, headers, ctx, timeout=120) as resp:
                body = resp.read().decode('utf-8', errors='replace')
        except HTTPError as e:
            raise BackupRestoreError(f'ClickHouse list tables failed HTTP {e.code}') from e
        except URLError as e:
            raise BackupRestoreError(f'ClickHouse list tables failed: {e.reason}') from e
        names = [ln.strip() for ln in body.splitlines() if ln.strip()]
        for n in names:
            if not _SAFE_IDENT.match(n):
                raise BackupRestoreError(f'Unsupported table name for export: {n!r}')
        return names

    def backup(self, params: Mapping[str, Any], dest: Path, **kwargs: Any) -> Path:
        db = params.get('database_name')
        if not db:
            raise BackupRestoreError('database_name is required for ClickHouse backup.')
        dest = Path(dest)
        if dest.suffix.lower() != '.zip':
            dest = dest.with_suffix('.zip')
        dest.parent.mkdir(parents=True, exist_ok=True)

        tables = self._list_tables(params, str(db))
        base, headers, ctx = self._http_base(params)

        with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                '_manifest.txt',
                'format=CSVWithNames+ddl\n' + '\n'.join(tables) + '\n',
                compress_type=zipfile.ZIP_STORED,
            )
            for table in tables:
                ddl_q = f'SHOW CREATE TABLE `{db}`.`{table}` FORMAT TabSeparatedRaw'
                try:
                    with self._post_sql(base, ddl_q, headers, ctx, timeout=300) as resp:
                        ddl = resp.read().decode('utf-8', errors='replace').strip()
                except HTTPError as e:
                    raise BackupRestoreError(
                        f'SHOW CREATE TABLE failed for {table!r}: HTTP {e.code}'
                    ) from e
                zf.writestr(f'schema/{table}.sql', ddl + '\n', compress_type=zipfile.ZIP_STORED)

                q = f'SELECT * FROM `{db}`.`{table}` FORMAT CSVWithNames'
                try:
                    with self._post_sql(base, q, headers, ctx, timeout=86400) as resp:
                        with zf.open(f'{table}.csv', 'w') as member:
                            shutil.copyfileobj(resp, member)
                except HTTPError as e:
                    raise BackupRestoreError(
                        f'Export failed for table {table!r}: HTTP {e.code}'
                    ) from e
                except URLError as e:
                    raise BackupRestoreError(
                        f'Export failed for table {table!r}: {e.reason}'
                    ) from e

        return dest

    def restore(
        self,
        params: Mapping[str, Any],
        src: Path,
        *,
        apply_schema: bool = False,
        truncate_first: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Restore data from a ZIP produced by :meth:`backup`.

        - ``apply_schema``: run ``schema/<table>.sql`` DDL files before insert (may fail if objects exist).
        - ``truncate_first``: ``TRUNCATE TABLE`` each table before ``INSERT`` (destructive).
        """
        db = params.get('database_name')
        if not db:
            raise BackupRestoreError('database_name is required for ClickHouse restore.')
        if not _SAFE_IDENT.match(str(db)):
            raise BackupRestoreError('database_name must be a simple identifier.')

        src = Path(src)
        if not src.is_file():
            raise BackupRestoreError(f'Backup file not found: {src}')

        base, headers, ctx = self._http_base(params)

        with zipfile.ZipFile(src, 'r') as zf:
            try:
                manifest_raw = zf.read('_manifest.txt').decode('utf-8')
            except KeyError as e:
                raise BackupRestoreError('Invalid ZIP: missing _manifest.txt') from e
            lines = [ln.strip() for ln in manifest_raw.splitlines() if ln.strip()]
            if not lines or not lines[0].startswith('format='):
                raise BackupRestoreError('Invalid backup manifest.')
            tables = lines[1:]

            for table in tables:
                if not _SAFE_IDENT.match(table):
                    raise BackupRestoreError(f'Invalid table name in manifest: {table!r}')

            if apply_schema:
                for table in tables:
                    path = f'schema/{table}.sql'
                    if path not in zf.namelist():
                        raise BackupRestoreError(
                            f'Missing {path} in archive; use a backup created with the current exporter.'
                        )
                    ddl = zf.read(path).decode('utf-8', errors='replace')
                    self._post_ddl(base, ddl, headers, ctx)

            for table in tables:
                csv_path = f'{table}.csv'
                if csv_path not in zf.namelist():
                    raise BackupRestoreError(f'Missing data file {csv_path} in archive.')
                csv_body = zf.read(csv_path)

                if truncate_first:
                    trunc_q = f'TRUNCATE TABLE `{db}`.`{table}`'
                    try:
                        with self._post_sql(base, trunc_q, headers, ctx, timeout=600) as resp:
                            if resp.status >= 400:
                                raise BackupRestoreError(
                                    f'TRUNCATE {table!r} HTTP {resp.status}'
                                )
                    except HTTPError as e:
                        raise BackupRestoreError(f'TRUNCATE {table!r} HTTP {e.code}') from e

                try:
                    self._post_insert_csv(base, str(db), table, csv_body, headers, ctx)
                except URLError as e:
                    raise BackupRestoreError(f'INSERT {table!r} failed: {e.reason}') from e
