"""Defense-in-depth for common.logging.StructuredFormatter — the module
docstring is explicit that callers are responsible for not logging
secrets in the first place, but a caller mistake (e.g. `extra={"password":
raw_password}`) should still not leak into the actual JSON log line for
a well-known set of sensitive key names."""

import json
import logging

from common.logging import StructuredFormatter


def _format(extra: dict) -> dict:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="something happened",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(StructuredFormatter().format(record))


def test_a_password_field_is_redacted():
    payload = _format({"password": "hunter2"})

    assert payload["extra"]["password"] == "[REDACTED]"
    assert "hunter2" not in json.dumps(payload)


def test_known_sensitive_key_variants_are_all_redacted():
    payload = _format(
        {
            "access_token": "abc.def.ghi",
            "refresh_token": "xyz",
            "api_key": "sk-live-123",
            "secret": "s3cret",
            "authorization": "Bearer abc",
        }
    )

    for key in payload["extra"]:
        assert payload["extra"][key] == "[REDACTED]"


def test_unrelated_fields_are_left_untouched():
    payload = _format({"document_id": "doc-1", "attempt_count": 3})

    assert payload["extra"]["document_id"] == "doc-1"
    assert payload["extra"]["attempt_count"] == 3


def test_redaction_is_case_insensitive():
    payload = _format({"Password": "hunter2", "API_KEY": "sk-live-123"})

    assert payload["extra"]["Password"] == "[REDACTED]"
    assert payload["extra"]["API_KEY"] == "[REDACTED]"
