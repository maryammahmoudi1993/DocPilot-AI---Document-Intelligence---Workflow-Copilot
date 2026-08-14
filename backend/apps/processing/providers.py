"""External-provider abstractions for the processing pipeline (project
rule: mock external providers at module boundaries; unit tests must
never call a paid OCR/embedding/LLM provider). Two interfaces:

- `OCRProvider` — turns a page/image into text. `TesseractOCRProvider`
  is the real implementation (requires the tesseract-ocr and
  poppler-utils system binaries — see Dockerfile); `MockOCRProvider` is
  a deterministic stand-in used everywhere those binaries aren't
  installed (tests, and any environment without DOCUMENT_OCR_PROVIDER=
  tesseract). Real-provider imports are lazy (inside the method, not at
  module level) specifically so importing this module — which
  `pipeline.py`/`tasks.py` always do — never requires those binaries;
  only actually calling TesseractOCRProvider does.
- `ClassificationProvider` — assigns a DocumentType.
  `KeywordClassificationProvider` is a deterministic heuristic (the
  default, and what unit tests exercise); `GeminiClassificationProvider`
  is a real Google Gemini call, active only when
  settings.DOCUMENT_CLASSIFICATION_PROVIDER == "gemini" — same
  lazy-import discipline as TesseractOCRProvider above, and its Gemini
  client construction is shared with apps.extraction.providers via
  common.gemini.build_gemini_client.
"""

from typing import TYPE_CHECKING, Protocol

from django.conf import settings

from apps.processing.exceptions import RetryableProcessingError, ValidationProcessingError
from apps.processing.models import DocumentType
from common.gemini import build_gemini_client

if TYPE_CHECKING:
    # Only for the type hint below — real imports of PIL stay lazy (see
    # the module docstring) even though Pillow is a listed dependency,
    # for consistency with pytesseract/pdf2image's lazy imports.
    from PIL.Image import Image


class OCRProvider(Protocol):
    def extract_text_from_page(self, *, pdf_bytes: bytes, page_number: int) -> str: ...

    def extract_text_from_image(self, *, image_bytes: bytes) -> str: ...


class MockOCRProvider:
    """Deterministic — returns a fixed marker string rather than
    attempting real image recognition. What matters to the pipeline's
    own tests is *which* pages/images get sent to OCR, not OCR's actual
    accuracy (that's a real-provider concern, not this codebase's)."""

    def extract_text_from_page(self, *, pdf_bytes: bytes, page_number: int) -> str:
        return f"[mock-ocr-text page {page_number}]"

    def extract_text_from_image(self, *, image_bytes: bytes) -> str:
        return "[mock-ocr-text]"


class TesseractOCRProvider:
    def extract_text_from_page(self, *, pdf_bytes: bytes, page_number: int) -> str:
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(pdf_bytes, first_page=page_number, last_page=page_number)
        if not images:
            return ""
        return self._ocr_image(images[0])

    def extract_text_from_image(self, *, image_bytes: bytes) -> str:
        import io

        from PIL import Image

        return self._ocr_image(Image.open(io.BytesIO(image_bytes)))

    @staticmethod
    def _ocr_image(image: "Image") -> str:
        import pytesseract

        return pytesseract.image_to_string(image)


def get_ocr_provider() -> OCRProvider:
    if settings.DOCUMENT_OCR_PROVIDER == "tesseract":
        return TesseractOCRProvider()
    return MockOCRProvider()


class ClassificationProvider(Protocol):
    def classify(self, *, filename: str, text_sample: str) -> str: ...


class KeywordClassificationProvider:
    """Deterministic keyword heuristic — a documented placeholder for a
    real LLM-based classifier a future phase may add behind this same
    interface. Not a network call; safe to run in unit tests."""

    _KEYWORDS: dict[str, str] = {
        "invoice": DocumentType.INVOICE,
        "contract": DocumentType.CONTRACT,
        "receipt": DocumentType.RECEIPT,
        "policy": DocumentType.POLICY,
        "report": DocumentType.REPORT,
        "form": DocumentType.FORM,
    }

    def classify(self, *, filename: str, text_sample: str) -> str:
        haystack = f"{filename} {text_sample}".lower()
        for keyword, document_type in self._KEYWORDS.items():
            if keyword in haystack:
                return document_type
        return DocumentType.UNKNOWN


class GeminiClassificationProvider:
    """Real LLM classification via Google Gemini. Only ever active when
    settings.DOCUMENT_CLASSIFICATION_PROVIDER == "gemini" — never the
    default, so a fresh checkout with no GEMINI_API_KEY set keeps
    working exactly as before. Costs real money per call; never
    exercised by unit tests (project rule) — see
    apps/processing/tests/test_gemini_classification.py, which
    monkeypatches build_gemini_client instead."""

    # Bounded for the same reason apps.processing.pipeline.stage_classify
    # only ever passes a 2000-char sample to the classifier in the first
    # place — this is a second, defensive cap in case a future caller
    # passes more.
    _MAX_TEXT_CHARS = 2000

    def classify(self, *, filename: str, text_sample: str) -> str:
        from google.genai import errors, types

        valid_types = [choice.value for choice in DocumentType if choice != DocumentType.UNKNOWN]
        prompt = (
            "You are classifying a business document. Respond with exactly one word: "
            f"one of [{', '.join(valid_types)}, unknown]. No punctuation, no explanation.\n\n"
            f"Filename: {filename}\n\n"
            f"Document text (may be partial):\n{text_sample[: self._MAX_TEXT_CHARS]}"
        )

        client = build_gemini_client()
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    # Deliberately generous for a one-word answer — even
                    # with thinking disabled below, a too-tight budget
                    # occasionally still clips the response before the
                    # answer token (finish_reason=MAX_TOKENS with empty
                    # text); confirmed against the real API, not a
                    # theoretical margin.
                    temperature=0,
                    max_output_tokens=100,
                    # Current Gemini models think by default; a small
                    # max_output_tokens budget on a thinking-enabled
                    # request gets consumed entirely by invisible
                    # reasoning tokens, leaving an empty response with
                    # finish_reason=MAX_TOKENS. This is a one-word
                    # classification, not a reasoning task — disable it.
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
        except errors.ServerError as exc:
            raise RetryableProcessingError(
                "Classification provider is temporarily unavailable.",
                code="classification_provider_unavailable",
            ) from exc
        except errors.ClientError as exc:
            raise ValidationProcessingError(
                "Classification provider rejected the request.",
                code="classification_provider_error",
            ) from exc

        answer = (response.text or "").strip().lower()
        return answer if answer in valid_types else DocumentType.UNKNOWN


def get_classification_provider() -> ClassificationProvider:
    if settings.DOCUMENT_CLASSIFICATION_PROVIDER == "gemini":
        return GeminiClassificationProvider()
    return KeywordClassificationProvider()
