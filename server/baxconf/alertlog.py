"""Backend operation logs (Django logging, not a UI)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger('baxauto.alert')


def log_alert(
    message: str,
    *,
    status: str = 'error',
    source: str = '',
    **context: Any,
) -> None:
    """
    Record an operator log line.

    ``status`` is ``success``, ``warning``, or ``error`` and selects the log level.
    """
    text = (message or 'Operation finished.').strip() or 'Operation finished.'
    parts = [f'status={status}']
    if source:
        parts.append(f'source={source}')
    for key, value in context.items():
        if value is None or value == '':
            continue
        parts.append(f'{key}={value}')
    line = f'{" ".join(parts)} {text}'
    if status == 'success':
        logger.info(line)
    elif status == 'warning':
        logger.warning(line)
    else:
        logger.error(line)


def log_http_alert(message: str, *, http_status: int, source: str = '', **context: Any) -> None:
    status = 'warning' if http_status in (401, 403, 404) else 'error'
    log_alert(message, status=status, source=source, http_status=http_status, **context)
