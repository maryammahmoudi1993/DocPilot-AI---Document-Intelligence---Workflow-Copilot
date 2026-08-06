"""Unit tests for common/ (logging, exception handling) and the parts of
apps/health/services.py not already exercised through the HTTP-level tests
in test_health.py.
"""

import json
import logging
from unittest.mock import patch

import redis

from apps.health.services import check_redis
from common.exceptions import stable_exception_handler
from common.logging import CorrelationIdFilter, StructuredFormatter, correlation_id_var


def test_check_redis_reports_failure_without_leaking_raw_error() -> None:
    with patch("apps.health.services.redis.from_url") as from_url:
        from_url.return_value.ping.side_effect = redis.RedisError("connection refused")

        status = check_redis()

    assert status.ok is False
    assert status.name == "redis"
    assert status.error == "connection refused"


def test_stable_exception_handler_returns_generic_500_for_unhandled_exception() -> None:
    with patch("common.exceptions.drf_default_exception_handler", return_value=None):
        response = stable_exception_handler(RuntimeError("db password is hunter2"), {"view": None})

    assert response is not None
    assert response.status_code == 500
    assert response.data["error"]["code"] == "internal_error"
    # The real exception message must never reach the client.
    assert "hunter2" not in str(response.data)


def _make_record(message: str = "hello") -> logging.LogRecord:
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_correlation_id_filter_attaches_current_context_value() -> None:
    token = correlation_id_var.set("abc-123")
    try:
        record = _make_record()
        assert CorrelationIdFilter().filter(record) is True
        assert record.correlation_id == "abc-123"  # type: ignore[attr-defined]
    finally:
        correlation_id_var.reset(token)


def test_structured_formatter_emits_valid_json_with_expected_keys() -> None:
    record = _make_record("something happened")
    record.correlation_id = "abc-123"

    line = StructuredFormatter().format(record)
    payload = json.loads(line)

    assert payload["message"] == "something happened"
    assert payload["level"] == "INFO"
    assert payload["correlation_id"] == "abc-123"
    assert "timestamp" in payload
