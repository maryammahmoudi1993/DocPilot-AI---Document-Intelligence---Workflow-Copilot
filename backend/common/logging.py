"""Structured logging support.

Emits one JSON object per log line (machine-parseable, correlation-ID
tagged) instead of Django's default free-text formatting. Never log
secrets, tokens, passwords, full document contents, or extracted field
values — callers are responsible for keeping log messages/extra fields free
of that data; this formatter does not attempt to redact after the fact.
"""

import contextvars
import json
import logging
from datetime import UTC, datetime

correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)

_RESERVED_LOG_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


class CorrelationIdFilter(logging.Filter):
    """Attach the current request's correlation ID to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True


class StructuredFormatter(logging.Formatter):
    """Render log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _RESERVED_LOG_RECORD_ATTRS and key != "correlation_id"
        }
        if extra:
            payload["extra"] = extra

        return json.dumps(payload, default=str)
