"""Test doubles for the provider interfaces (apps/processing/providers.py)
— project rule: mock external providers at module boundaries. Neither
of these touches tesseract, pdf2image, or a real classifier/LLM.
"""


class FakeOCRProvider:
    """Records every call it receives (page number or "image") so tests
    can assert exactly which pages were sent to OCR — the core evidence
    that digital pages are skipped and only flagged pages are OCR'd.
    `fail_times` lets a test simulate a transient provider failure that
    succeeds on retry (or never, if set high enough).
    """

    def __init__(
        self,
        *,
        text: str = "ocr-extracted-text",
        fail_times: int = 0,
        error: Exception | None = None,
    ):
        self.page_calls: list[int] = []
        self.image_calls: int = 0
        self._text = text
        self._fail_times = fail_times
        self._error = error

    def extract_text_from_page(self, *, pdf_bytes: bytes, page_number: int) -> str:
        self.page_calls.append(page_number)
        if self._fail_times > 0:
            self._fail_times -= 1
            raise self._error  # type: ignore[misc]
        return f"{self._text} (page {page_number})"

    def extract_text_from_image(self, *, image_bytes: bytes) -> str:
        self.image_calls += 1
        if self._fail_times > 0:
            self._fail_times -= 1
            raise self._error  # type: ignore[misc]
        return self._text


class FakeClassificationProvider:
    def __init__(self, *, result: str = "unknown"):
        self.calls: list[tuple[str, str]] = []
        self._result = result

    def classify(self, *, filename: str, text_sample: str) -> str:
        self.calls.append((filename, text_sample))
        return self._result
