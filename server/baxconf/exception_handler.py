"""DRF exception handler that writes an alert log for failed API operations."""

from __future__ import annotations

from rest_framework.exceptions import NotAuthenticated
from rest_framework.views import exception_handler

from baxconf.alertlog import log_alert, log_http_alert


def _message_from_data(data) -> str:
    if data is None:
        return ''
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        detail = data.get('detail')
        if isinstance(detail, str):
            return detail
        if detail is not None:
            return str(detail)
        return str(data)
    if isinstance(data, list):
        return '; '.join(str(item) for item in data)
    return str(data)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    # Missing credentials is routine; bad-password / other failures still log.
    if isinstance(exc, NotAuthenticated):
        return response

    view = context.get('view')
    request = context.get('request')
    source = type(view).__name__ if view is not None else 'api'
    path = getattr(request, 'path', '')
    method = getattr(request, 'method', '')

    if response is None:
        log_alert(
            str(exc) or exc.__class__.__name__,
            status='error',
            source=source,
            method=method,
            path=path,
        )
        return None

    if response.status_code >= 400:
        log_http_alert(
            _message_from_data(response.data) or str(exc),
            http_status=response.status_code,
            source=source,
            method=method,
            path=path,
        )
    return response
