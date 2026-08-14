"""common.gemini — the shared Gemini client-construction helper used by
the real (non-mock) classification and extraction providers. Only
checks that the module is importable and that it builds a client with
the configured API key — never a real network call (project rule: unit
tests must not call paid providers)."""

from unittest.mock import patch


def test_build_gemini_client_uses_the_configured_api_key(settings):
    settings.GEMINI_API_KEY = "test-key-123"

    with patch("google.genai.Client") as mock_client_cls:
        from common.gemini import build_gemini_client

        build_gemini_client()

    mock_client_cls.assert_called_once_with(api_key="test-key-123")
