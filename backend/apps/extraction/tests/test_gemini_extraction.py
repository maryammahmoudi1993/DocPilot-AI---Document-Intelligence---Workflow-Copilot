"""GeminiExtractionProvider — a real-LLM structured-extraction provider
behind the same ExtractionProvider interface as
RegexInvoiceExtractionProvider. Never calls the real Gemini API
(project rule) — `common.gemini.build_gemini_client` is monkeypatched
to a fake client at the module boundary."""

import json
from unittest.mock import MagicMock

import pytest

from apps.extraction.providers import (
    INVOICE_SCHEMA,
    GeminiExtractionProvider,
    get_extraction_provider,
)


def _fake_client(payload: dict) -> MagicMock:
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text=json.dumps(payload))
    return client


def _full_payload(**overrides) -> dict:
    payload = {key: {"value": "", "confidence": 0.0} for key, _, _ in INVOICE_SCHEMA}
    payload.update(overrides)
    return payload


class TestGeminiExtractionProvider:
    def test_maps_the_model_response_onto_every_schema_field(self, monkeypatch):
        payload = _full_payload(
            total={"value": "2,422.64", "confidence": 0.95},
            vendor_name={"value": "Northwind Office Supply Co.", "confidence": 0.9},
        )
        monkeypatch.setattr(
            "apps.extraction.providers.build_gemini_client", lambda: _fake_client(payload)
        )

        results = {r.key: r for r in GeminiExtractionProvider().extract(text="irrelevant")}

        assert results["total"].value == "2,422.64"
        assert results["total"].confidence == 0.95
        assert results["vendor_name"].value == "Northwind Office Supply Co."
        assert {r.key for r in results.values()} == {key for key, _, _ in INVOICE_SCHEMA}

    def test_missing_field_in_the_response_comes_back_empty(self, monkeypatch):
        payload = _full_payload()
        del payload["due_date"]
        monkeypatch.setattr(
            "apps.extraction.providers.build_gemini_client", lambda: _fake_client(payload)
        )

        results = {r.key: r for r in GeminiExtractionProvider().extract(text="x")}

        assert results["due_date"].value == ""
        assert results["due_date"].confidence == 0.0

    def test_confidence_is_clamped_to_the_valid_range(self, monkeypatch):
        payload = _full_payload(total={"value": "10.00", "confidence": 5.0})
        monkeypatch.setattr(
            "apps.extraction.providers.build_gemini_client", lambda: _fake_client(payload)
        )

        results = {r.key: r for r in GeminiExtractionProvider().extract(text="x")}

        assert results["total"].confidence == 1.0

    def test_an_empty_value_always_reports_zero_confidence_even_if_the_model_disagrees(
        self, monkeypatch
    ):
        payload = _full_payload(total={"value": "", "confidence": 0.8})
        monkeypatch.setattr(
            "apps.extraction.providers.build_gemini_client", lambda: _fake_client(payload)
        )

        results = {r.key: r for r in GeminiExtractionProvider().extract(text="x")}

        assert results["total"].confidence == 0.0

    def test_a_provider_failure_raises_rather_than_returning_fabricated_data(self, monkeypatch):
        client = MagicMock()
        client.models.generate_content.side_effect = RuntimeError("boom")
        monkeypatch.setattr("apps.extraction.providers.build_gemini_client", lambda: client)

        with pytest.raises(Exception):  # noqa: B017 - any failure must propagate, not be swallowed here
            GeminiExtractionProvider().extract(text="x")

    def test_truncates_very_long_input_text_before_sending_it(self, monkeypatch):
        client = _fake_client(_full_payload())
        monkeypatch.setattr("apps.extraction.providers.build_gemini_client", lambda: client)

        GeminiExtractionProvider().extract(text="z" * 50_000)

        call_kwargs = client.models.generate_content.call_args.kwargs
        assert len(call_kwargs["contents"]) < 50_000


class TestGetExtractionProvider:
    def test_defaults_to_the_regex_provider(self, settings):
        settings.DOCUMENT_EXTRACTION_PROVIDER = "regex"
        from apps.extraction.providers import RegexInvoiceExtractionProvider

        assert isinstance(get_extraction_provider(), RegexInvoiceExtractionProvider)

    def test_returns_gemini_when_configured(self, settings):
        settings.DOCUMENT_EXTRACTION_PROVIDER = "gemini"

        assert isinstance(get_extraction_provider(), GeminiExtractionProvider)

    def test_falls_back_to_regex_for_any_other_value(self, settings):
        settings.DOCUMENT_EXTRACTION_PROVIDER = "something-unrecognized"
        from apps.extraction.providers import RegexInvoiceExtractionProvider

        assert isinstance(get_extraction_provider(), RegexInvoiceExtractionProvider)
