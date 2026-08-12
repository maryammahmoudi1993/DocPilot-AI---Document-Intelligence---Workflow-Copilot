"""Structured logging support.

Emits one JSON object per log line (machine-parseable, correlation-ID
tagged) instead of Django's default free-text formatting. Callers are
still primarily responsible for keeping log messages/extra fields free
of secrets, tokens, passwords, full document contents, or extracted
field values — this formatter's redaction (see `_SENSITIVE_KEY_PATTERN`
below) is a defense-in-depth safety net for a caller mistake (e.g.
`extra={"password": raw_password}`), not a substitute for that
discipline: it only catches well-known key *names*, not secrets hiding
inside an unrelated field's value.
"""

import contextvars
import json
import logging
import re
from datetime import UTC, datetime

correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)

_RESERVED_LOG_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|token|secret|api[_-]?key|authorization|credential)", re.IGNORECASE
)
_REDACTED = "[REDACTED]"


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
            key: (_REDACTED if _SENSITIVE_KEY_PATTERN.search(key) else value)
            for key, value in record.__dict__.items()
            if key not in _RESERVED_LOG_RECORD_ATTRS and key != "correlation_id"
        }
        if extra:
            payload["extra"] = extra

        return json.dumps(payload, default=str)
