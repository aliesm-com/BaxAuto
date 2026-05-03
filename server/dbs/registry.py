"""
Maps **database engine** → implementation module (``dbs.<engine>.backend``).

We intentionally use **one handler per engine family**: vendor CLI tools (``pg_dump``,
``mysqldump``, ``mongodump``, …) already track server capabilities when client and server
majors are paired correctly.

``version`` is kept on the public API for logging or **future** forks only — add an override
table here if a specific release ever needs different flags or binaries.
"""

from __future__ import annotations

from typing import Tuple

_ENGINE_MODULES: dict[str, str] = {
    'postgresql': 'dbs.postgresql.backend',
    'postgres': 'dbs.postgresql.backend',
    'mysql': 'dbs.mysql.backend',
    'mariadb': 'dbs.mariadb.backend',
    'redis': 'dbs.redis.backend',
    'rabbitmq': 'dbs.rabbitmq.backend',
    'clickhouse': 'dbs.clickhouse.backend',
    'sqlserver': 'dbs.sqlserver.backend',
    'mongodb': 'dbs.mongodb.backend',
}


def normalize_engine(engine: str) -> str:
    e = engine.strip().lower()
    if e == 'postgres':
        return 'postgresql'
    return e


def resolve_backend_module(engine: str, version: str | None = None) -> str:
    """Return dotted path to module defining class ``Backend``."""
    key = normalize_engine(engine)
    if key not in _ENGINE_MODULES:
        raise ValueError(f'Unknown database engine: {engine!r}')
    _ = version  # reserved for future per-version routing
    return _ENGINE_MODULES[key]


def parse_engine_version(engine: str, version: str) -> Tuple[str, str]:
    return normalize_engine(engine), version.strip()
