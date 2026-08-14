"""GeminiClassificationProvider — a real-LLM classifier behind the same
ClassificationProvider interface as KeywordClassificationProvider.
Never calls the real Gemini API (project rule) — `common.gemini.
build_gemini_client` is monkeypatched to a fake client at the module
boundary, mirroring how TesseractOCRProvider's tests avoid real OCR."""

from unittest.mock import MagicMock

import pytest

from apps.processing.exceptions import RetryableProcessingError, ValidationProcessingError
from apps.processing.providers import (
    GeminiClassificationProvider,
    get_classification_provider,
)


def _fake_client(response_text: str) -> MagicMock:
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text=response_text)
    return client


class TestGeminiClassificationProvider:
    def test_returns_the_document_type_the_model_names(self, monkeypatch):
        client = _fake_client("invoice")
        monkeypatch.setattr("apps.processing.providers.build_gemini_client", lambda: client)

        result = GeminiClassificationProvider().classify(
            filename="scan-0142.pdf", text_sample="some ambiguous content"
        )

        assert result == "invoice"

    def test_is_case_and_whitespace_insensitive(self, monkeypatch):
        client = _fake_client("  Contract\n")
        monkeypatch.setattr("apps.processing.providers.build_gemini_client", lambda: client)

        result = GeminiClassificationProvider().classify(filename="x.pdf", text_sample="")

        assert result == "contract"

    def test_falls_back_to_unknown_for_an_unrecognized_answer(self, monkeypatch):
        client = _fake_client("something the model made up")
        monkeypatch.setattr("apps.processing.providers.build_gemini_client", lambda: client)

        result = GeminiClassificationProvider().classify(filename="x.pdf", text_sample="")

        assert result == "unknown"

    def test_never_sends_more_than_the_bounded_text_sample(self, monkeypatch):
        client = _fake_client("invoice")
        monkeypatch.setattr("apps.processing.providers.build_gemini_client", lambda: client)

        GeminiClassificationProvider().classify(filename="x.pdf", text_sample="y" * 5000)

        call_kwargs = client.models.generate_content.call_args.kwargs
        assert "y" * 5000 not in call_kwargs["contents"]

    def test_a_server_error_is_wrapped_as_retryable(self, monkeypatch):
        from google.genai import errors

        client = MagicMock()
        client.models.generate_content.side_effect = errors.ServerError(
            503, {"error": {"message": "unavailable"}}
        )
        monkeypatch.setattr("apps.processing.providers.build_gemini_client", lambda: client)

        with pytest.raises(RetryableProcessingError):
            GeminiClassificationProvider().classify(filename="x.pdf", text_sample="")

    def test_a_client_error_is_not_retryable(self, monkeypatch):
        from google.genai import errors

        client = MagicMock()
        client.models.generate_content.side_effect = errors.ClientError(
            400, {"error": {"message": "bad request"}}
        )
        monkeypatch.setattr("apps.processing.providers.build_gemini_client", lambda: client)

        with pytest.raises(ValidationProcessingError):
            GeminiClassificationProvider().classify(filename="x.pdf", text_sample="")


class TestGetClassificationProvider:
    def test_defaults_to_the_keyword_heuristic(self, settings):
        settings.DOCUMENT_CLASSIFICATION_PROVIDER = "keyword"
        from apps.processing.providers import KeywordClassificationProvider

        assert isinstance(get_classification_provider(), KeywordClassificationProvider)

    def test_returns_gemini_when_configured(self, settings):
        settings.DOCUMENT_CLASSIFICATION_PROVIDER = "gemini"

        assert isinstance(get_classification_provider(), GeminiClassificationProvider)

    def test_falls_back_to_keyword_for_any_other_value(self, settings):
        settings.DOCUMENT_CLASSIFICATION_PROVIDER = "something-unrecognized"
        from apps.processing.providers import KeywordClassificationProvider

        assert isinstance(get_classification_provider(), KeywordClassificationProvider)
