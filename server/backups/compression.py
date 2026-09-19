"""Gzip helpers for backup artifacts."""

from __future__ import annotations

import gzip
import os
import shutil
import tempfile
from pathlib import Path

ALREADY_COMPRESSED_SUFFIXES = {'.gz', '.zip', '.bz2', '.xz', '.zst'}


def gzip_if_requested(path: Path, compress: bool) -> Path:
    """If ``compress`` is set, replace ``path`` with a ``.gz`` sibling (unless already packed)."""
    if not compress:
        return path
    if path.suffix.lower() in ALREADY_COMPRESSED_SUFFIXES:
        return path
    dest = path.with_name(path.name + '.gz')
    with path.open('rb') as src, gzip.open(dest, 'wb', compresslevel=6) as out:
        shutil.copyfileobj(src, out)
    path.unlink(missing_ok=True)
    return dest


def looks_gzipped(path: Path, compressed_flag: bool) -> bool:
    return bool(compressed_flag) or path.suffix.lower() == '.gz'


def gunzip_to_temp(path: Path) -> Path:
    """Decompress ``path`` to a NamedTemporaryFile; caller must unlink."""
    inner = path.name[:-3] if path.name.lower().endswith('.gz') else path.name
    suffix = Path(inner).suffix or '.bin'
    fd, tmp_name = tempfile.mkstemp(prefix='baxauto-restore-', suffix=suffix)
    tmp = Path(tmp_name)
    try:
        os.close(fd)
        with gzip.open(path, 'rb') as src, tmp.open('wb') as dst:
            shutil.copyfileobj(src, dst)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return tmp
