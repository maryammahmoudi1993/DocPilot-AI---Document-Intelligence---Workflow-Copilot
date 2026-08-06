"""Request-scoped middleware shared across the whole project.

Kept deliberately thin — no business logic lives here (see the project's
non-negotiable rule keeping business logic out of views/serializers/
middleware). This module only propagates a correlation ID for log
correlation.
"""

import uuid

from django.http import HttpRequest, HttpResponse

from common.logging import correlation_id_var

CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware:
    """Attach a correlation ID to every request/response pair.

    Reuses an inbound `X-Correlation-ID` header when present (so a request
    can be traced across services), otherwise generates a new UUID4. The ID
    is stored in a context variable for the duration of the request so
    `common.logging.CorrelationIdFilter` can attach it to every log record
    emitted while handling the request, and it is echoed back on the
    response for the caller to correlate with.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        token = correlation_id_var.set(correlation_id)
        # HttpRequest doesn't declare this attribute; attached dynamically
        # so views/logging can read the correlation ID off the request.
        request.correlation_id = correlation_id  # type: ignore[attr-defined]
        try:
            response = self.get_response(request)
        finally:
            correlation_id_var.reset(token)
        response[CORRELATION_ID_HEADER] = correlation_id
        return response
