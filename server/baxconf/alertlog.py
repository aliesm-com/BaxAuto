"""Backend operation logs, persisted alerts, and optional outbound webhook."""

from __future__ import annotations

import json
import logging
import sys
import threading
from typing import Any

from django.conf import settings

logger = logging.getLogger('baxauto.alert')

_WEBHOOK_STATUSES = {
    'success': 'up',
    'warning': 'degraded',
    'error': 'down',
}


def webhook_status_for(status: str) -> str:
    return _WEBHOOK_STATUSES.get(status, 'down')


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
    Errors and warnings are stored for the dashboard and posted to ``ALERT_WEBHOOK_URL``.
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

    if status in ('error', 'warning'):
        error = _error_label(source=source, context=context)
        _persist_alert(text, status=status, source=source, error=error, context=context)
        _dispatch_webhook(
            {
                'status': webhook_status_for(status),
                'error': error,
                'description': text,
            }
        )


def log_http_alert(message: str, *, http_status: int, source: str = '', **context: Any) -> None:
    status = 'warning' if http_status in (401, 403, 404) else 'error'
    log_alert(message, status=status, source=source, http_status=http_status, **context)


_SOURCE_ERRORS = {
    'backup': 'backup failed',
    'restore': 'restore failed',
    'schedule': 'schedule failed',
    'storage': 'storage error',
    'backup_download': 'download failed',
    'connection': 'connection error',
    'connection_test': 'connection test failed',
}


def _error_label(*, source: str, context: dict[str, Any]) -> str:
    raw = context.get('error')
    if raw:
        return str(raw)[:255]
    if source:
        return _SOURCE_ERRORS.get(source, source.replace('_', ' '))[:255]
    return 'error'


def _jsonable(context: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in context.items():
        if value is None or value == '':
            continue
        try:
            json.dumps(value)
            out[key] = value
        except TypeError:
            out[key] = str(value)
    return out


def _persist_alert(
    description: str,
    *,
    status: str,
    source: str,
    error: str,
    context: dict[str, Any],
) -> None:
    try:
        from backups.models import AlertEvent

        AlertEvent.objects.create(
            status=status,
            source=source or '',
            error=error,
            description=description,
            context=_jsonable(context),
        )
    except Exception:
        logger.warning('Failed to persist alert event', exc_info=True)


def _in_tests() -> bool:
    return 'test' in sys.argv or getattr(settings, 'TESTING', False)


def _dispatch_webhook(payload: dict[str, str]) -> None:
    url = (getattr(settings, 'ALERT_WEBHOOK_URL', '') or '').strip()
    if not url or _in_tests():
        return
    token = (getattr(settings, 'ALERT_WEBHOOK_TOKEN', '') or '').strip()
    timeout = int(getattr(settings, 'ALERT_WEBHOOK_TIMEOUT', 15) or 15)
    if getattr(settings, 'ALERT_WEBHOOK_SYNC', False):
        _post_webhook(url, token, payload, timeout)
        return
    threading.Thread(
        target=_post_webhook,
        args=(url, token, payload, timeout),
        daemon=True,
        name='alert-webhook',
    ).start()


def _post_webhook(url: str, token: str, payload: dict[str, str], timeout: int) -> None:
    try:
        import requests

        headers = {}
        if token:
            headers['X-Webhook-Token'] = token
        requests.post(url, headers=headers, json=payload, timeout=timeout)
    except Exception:
        logger.warning('Alert webhook delivery failed', exc_info=True)
