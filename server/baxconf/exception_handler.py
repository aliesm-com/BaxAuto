"""DRF exception handler that writes an alert log for failed API operations."""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import NotAuthenticated
from rest_framework.exceptions import ValidationError as DRFValidationError
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


def _django_validation_as_drf(exc: DjangoValidationError) -> DRFValidationError:
    if hasattr(exc, 'message_dict') and exc.message_dict:
        return DRFValidationError(exc.message_dict)
    if hasattr(exc, 'messages'):
        return DRFValidationError(list(exc.messages))
    return DRFValidationError(str(exc))


def api_exception_handler(exc, context):
    # Model.full_clean() raises Django ValidationError; convert before DRF handling.
    if isinstance(exc, DjangoValidationError) and not isinstance(exc, DRFValidationError):
        exc = _django_validation_as_drf(exc)

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
