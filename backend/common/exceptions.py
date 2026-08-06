"""Stable API error envelope for the whole project.

Wraps DRF's default exception handler so every error response — from every
app — has the same shape:

    {"error": {"code": "<stable_code>", "message": "<safe message>", "details": {...}}}

`code` is a stable machine-readable identifier that frontend code and API
consumers can branch on; it must not change when the underlying exception
message changes. Internal exception details (stack traces, database error
text, etc.) are never exposed to the client — unhandled exceptions are
logged server-side (with the request's correlation ID) and returned as a
generic `internal_error`.
"""

import logging

from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_exception_handler

logger = logging.getLogger(__name__)

_CODE_BY_EXCEPTION_CLASS: dict[type[Exception], str] = {
    drf_exceptions.ValidationError: "validation_error",
    drf_exceptions.NotAuthenticated: "not_authenticated",
    drf_exceptions.AuthenticationFailed: "authentication_failed",
    drf_exceptions.PermissionDenied: "permission_denied",
    drf_exceptions.NotFound: "not_found",
    drf_exceptions.MethodNotAllowed: "method_not_allowed",
    drf_exceptions.NotAcceptable: "not_acceptable",
    drf_exceptions.UnsupportedMediaType: "unsupported_media_type",
    drf_exceptions.Throttled: "throttled",
    drf_exceptions.ParseError: "parse_error",
}


def _stable_code_for(exc: Exception) -> str:
    for exc_class, code in _CODE_BY_EXCEPTION_CLASS.items():
        if isinstance(exc, exc_class):
            return code
    return "error"


def stable_exception_handler(exc: Exception, context: dict) -> Response | None:
    response = drf_default_exception_handler(exc, context)

    if response is None:
        # Not a DRF-recognized exception: an unexpected server error.
        # Log with the stack trace (server-side only) but never leak it
        # to the client.
        logger.exception("Unhandled exception in %s", context.get("view"))
        return Response(
            {"error": {"code": "internal_error", "message": "An unexpected error occurred."}},
            status=500,
        )

    response.data = {
        "error": {
            "code": _stable_code_for(exc),
            "message": str(exc.detail) if hasattr(exc, "detail") else str(exc),
            "details": response.data if isinstance(response.data, (dict, list)) else None,
        }
    }
    return response
