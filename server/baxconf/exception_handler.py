"""DRF exception handler that writes an alert log for failed API operations."""

from __future__ import annotations

import logging
import traceback

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

from baxconf.alertlog import log_alert, log_http_alert

logger = logging.getLogger('baxauto.api')


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

    # Unhandled exception → DRF would hide it as generic 500. Surface the real error.
    if response is None:
        tb = traceback.format_exc()
        detail = f'{exc.__class__.__name__}: {exc}'
        logger.error(
            'API unhandled error %s %s → %s\n%s',
            method,
            path,
            detail,
            tb,
        )
        log_alert(
            detail,
            status='error',
            source=source,
            method=method,
            path=path,
        )
        return Response(
            {
                'detail': detail,
                'exception': exc.__class__.__name__,
                'path': path,
                'method': method,
                'traceback': tb.splitlines()[-40:],
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if response.status_code >= 400:
        log_http_alert(
            _message_from_data(response.data) or str(exc),
            http_status=response.status_code,
            source=source,
            method=method,
            path=path,
        )
        if response.status_code >= 500:
            logger.error(
                'API %s %s → %s %s',
                method,
                path,
                response.status_code,
                _message_from_data(response.data) or str(exc),
            )
    return response
