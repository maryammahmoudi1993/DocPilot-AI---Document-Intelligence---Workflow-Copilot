"""Unit tests for the deterministic parts of apps/processing/providers.py
— MockOCRProvider, KeywordClassificationProvider, and the two factory
functions. `TesseractOCRProvider`'s actual OCR calls are deliberately
NOT exercised here (they'd need the real tesseract-ocr/poppler-utils
system binaries — see the Dockerfile — which this test environment
doesn't have and shouldn't need); only that the factory returns the
right *type* is checked.
"""

from apps.processing.providers import (
    KeywordClassificationProvider,
    MockOCRProvider,
    TesseractOCRProvider,
    get_classification_provider,
    get_ocr_provider,
)


class TestGetOcrProvider:
    def test_defaults_to_mock_when_unset(self, settings):
        settings.DOCUMENT_OCR_PROVIDER = "mock"
        assert isinstance(get_ocr_provider(), MockOCRProvider)

    def test_returns_tesseract_when_configured(self, settings):
        settings.DOCUMENT_OCR_PROVIDER = "tesseract"
        assert isinstance(get_ocr_provider(), TesseractOCRProvider)

    def test_falls_back_to_mock_for_any_other_value(self, settings):
        settings.DOCUMENT_OCR_PROVIDER = "something-unrecognized"
        assert isinstance(get_ocr_provider(), MockOCRProvider)


def test_get_classification_provider_returns_the_keyword_heuristic():
    assert isinstance(get_classification_provider(), KeywordClassificationProvider)


class TestMockOCRProvider:
    def test_extract_text_from_page_includes_the_page_number(self):
        provider = MockOCRProvider()
        assert "page 3" in provider.extract_text_from_page(pdf_bytes=b"", page_number=3)

    def test_extract_text_from_image_returns_a_marker_string(self):
        provider = MockOCRProvider()
        assert provider.extract_text_from_image(image_bytes=b"") != ""


class TestKeywordClassificationProvider:
    provider = KeywordClassificationProvider()

    def test_classifies_by_filename_keyword(self):
        assert self.provider.classify(filename="acme-invoice-2026.pdf", text_sample="") == "invoice"

    def test_classifies_by_text_content_keyword(self):
        result = self.provider.classify(
            filename="doc.pdf", text_sample="This receipt confirms payment."
        )
        assert result == "receipt"

    def test_falls_back_to_unknown_with_no_matching_keyword(self):
        result = self.provider.classify(
            filename="scan-0142.pdf", text_sample="random unrelated content"
        )
        assert result == "unknown"
