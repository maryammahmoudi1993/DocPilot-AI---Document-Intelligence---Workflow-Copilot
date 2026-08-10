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
- `ClassificationProvider` — assigns a DocumentType. Deliberately a
  keyword heuristic in this phase, not an LLM call — Phase 5/6 may
  introduce a real model-backed classifier behind this same interface
  without the pipeline changing.
"""

from typing import TYPE_CHECKING, Protocol

from django.conf import settings

from apps.processing.models import DocumentType

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


def get_classification_provider() -> ClassificationProvider:
    return KeywordClassificationProvider()
