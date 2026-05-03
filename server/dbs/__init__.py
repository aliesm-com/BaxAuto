"""
Database backends: class-based ``Backend`` per engine (backup, restore, test_connection).

The ``version`` argument is optional and reserved for future per-release routing.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Mapping

from dbs.base import BackupRestoreError, DatabaseBackend
from dbs.registry import resolve_backend_module

__all__ = [
    'BackupRestoreError',
    'DatabaseBackend',
    'backup',
    'get_backend',
    'resolve_backend_module',
    'restore',
    'test_connection',
]


def import_backend_module(engine: str, version: str | None = None):
    path = resolve_backend_module(engine, version)
    return importlib.import_module(path)


def get_backend(engine: str, version: str | None = None) -> DatabaseBackend:
    """Instantiate the ``Backend`` class from ``dbs.<engine>.backend``."""
    mod = import_backend_module(engine, version)
    cls = getattr(mod, 'Backend', None)
    if cls is None or not isinstance(cls, type):
        raise TypeError(f'Module {mod.__name__!r} must define a Backend class.')
    if not issubclass(cls, DatabaseBackend):
        raise TypeError(f'{cls!r} must inherit from DatabaseBackend.')
    return cls()


def test_connection(engine: str, params: Mapping[str, Any], *, version: str | None = None) -> None:
    """Run the engine's connectivity/credential check."""
    get_backend(engine, version).test_connection(params)


def backup(
    engine: str,
    params: Mapping[str, Any],
    *,
    dest: str | Path,
    version: str | None = None,
    **kwargs: Any,
) -> Path:
    return get_backend(engine, version).backup(params, Path(dest), **kwargs)


def restore(
    engine: str,
    params: Mapping[str, Any],
    *,
    src: str | Path,
    version: str | None = None,
    **kwargs: Any,
) -> None:
    get_backend(engine, version).restore(params, Path(src), **kwargs)
