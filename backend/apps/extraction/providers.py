"""Structured-extraction provider abstraction (project rule: mock
external providers at module boundaries). `RegexInvoiceExtractionProvider`
is a deterministic, no-network stand-in for a real document-AI/LLM
extraction call — it looks for `Label: value` style lines in the
combined OCR/digital text produced by apps.processing.pipeline. It is
intentionally simple and remains the default: a regex provider keeps
every test in this app fast and deterministic (no paid provider calls).

`GeminiExtractionProvider` is the real LLM alternative, active only
when settings.DOCUMENT_EXTRACTION_PROVIDER == "gemini" — it reads the
same combined text (not the raw PDF; see its own docstring for why) and
asks Gemini to return the same INVOICE_SCHEMA fields as structured JSON,
which is what actually generalizes to real invoices with varied
layouts that the regex provider's `Label: value` assumption can't
handle."""

import json
import re
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings

from common.gemini import build_gemini_client

# Invoice schema: (field key, human label, is_required). Order also
# drives the display order in the API response.
INVOICE_SCHEMA: list[tuple[str, str, bool]] = [
    ("vendor_name", "Vendor name", True),
    ("invoice_number", "Invoice number", True),
    ("invoice_date", "Invoice date", True),
    ("due_date", "Due date", False),
    ("subtotal", "Subtotal", False),
    ("tax", "Tax", False),
    ("discount", "Discount", False),
    ("total", "Total", True),
]


@dataclass(frozen=True)
class ExtractedFieldResult:
    key: str
    label: str
    value: str
    confidence: float
    is_required: bool


class ExtractionProvider(Protocol):
    def extract(self, *, text: str) -> list[ExtractedFieldResult]: ...


# One capture pattern per field key: the label(s) it looks for, matched
# case-insensitively at the start of a line, followed by a colon/dash
# and the value up to end of line.
_FIELD_PATTERNS: dict[str, re.Pattern[str]] = {
    "vendor_name": re.compile(r"(?im)^\s*vendor(?:\s*name)?\s*[:\-]\s*(.+)$"),
    "invoice_number": re.compile(r"(?im)^\s*invoice\s*(?:number|no\.?|#)\s*[:\-]\s*(.+)$"),
    "invoice_date": re.compile(r"(?im)^\s*invoice\s*date\s*[:\-]\s*(.+)$"),
    "due_date": re.compile(r"(?im)^\s*due\s*date\s*[:\-]\s*(.+)$"),
    "subtotal": re.compile(r"(?im)^\s*subtotal\s*[:\-]\s*(.+)$"),
    "tax": re.compile(r"(?im)^\s*tax\s*[:\-]\s*(.+)$"),
    "discount": re.compile(r"(?im)^\s*discount\s*[:\-]\s*(.+)$"),
    "total": re.compile(r"(?im)^\s*total\s*[:\-]\s*(.+)$"),
}


class RegexInvoiceExtractionProvider:
    """Deterministic: the same input text always yields the same output
    — required for the deterministic mocked test set and for
    idempotent re-processing (see services.build_extraction_for_job)."""

    def extract(self, *, text: str) -> list[ExtractedFieldResult]:
        results: list[ExtractedFieldResult] = []
        for key, label, is_required in INVOICE_SCHEMA:
            pattern = _FIELD_PATTERNS[key]
            match = pattern.search(text)
            if match:
                value = match.group(1).strip()
                results.append(
                    ExtractedFieldResult(
                        key=key, label=label, value=value, confidence=0.92, is_required=is_required
                    )
                )
            else:
                results.append(
                    ExtractedFieldResult(
                        key=key, label=label, value="", confidence=0.0, is_required=is_required
                    )
                )
        return results


_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        key: {
            "type": "object",
            "properties": {
                "value": {
                    "type": "string",
                    "description": "The field's value exactly as it appears in the "
                    "document, or an empty string if the field is not present.",
                },
                "confidence": {
                    "type": "number",
                    "description": "0.0-1.0: how confident you are this value is "
                    "correct. 0.0 if the field was not found.",
                },
            },
            "required": ["value", "confidence"],
        }
        for key, _, _ in INVOICE_SCHEMA
    },
    "required": [key for key, _, _ in INVOICE_SCHEMA],
}


class GeminiExtractionProvider:
    """Real LLM structured extraction via Google Gemini. Only active
    when settings.DOCUMENT_EXTRACTION_PROVIDER == "gemini"; never the
    default and never exercised by unit tests (project rule) — see
    apps/extraction/tests/test_gemini_extraction.py, which
    monkeypatches build_gemini_client instead.

    Deliberately reads the pipeline's already-extracted combined text
    (digital-text + OCR), the same input RegexInvoiceExtractionProvider
    gets, rather than sending the raw PDF bytes directly — this keeps
    the ExtractionProvider boundary and apps.extraction.services'
    call site unchanged (text in, fields out), so switching providers
    never touches the pipeline or storage layer. A future phase could
    extend this same interface to accept the source bytes for true
    multimodal (vision) extraction if text-based accuracy proves
    insufficient on real scanned invoices; that's a larger, separate
    change (plumbing file bytes through apps.processing.pipeline into
    apps.extraction.services), not made here."""

    # Bounds cost/latency on unusually long documents — well past what
    # a real invoice needs (the schema's fields are almost always on
    # the first page or two).
    _MAX_TEXT_CHARS = 8000

    def extract(self, *, text: str) -> list[ExtractedFieldResult]:
        from google.genai import types

        schema_description = "\n".join(
            f"- {key} ({label}){' [required]' if is_required else ''}"
            for key, label, is_required in INVOICE_SCHEMA
        )
        prompt = (
            "Extract the following fields from this invoice. For each field, "
            "return the value exactly as written in the document (or an empty "
            "string if absent) and your confidence (0.0-1.0) that it's correct.\n\n"
            f"Fields:\n{schema_description}\n\n"
            f"Document text:\n{text[: self._MAX_TEXT_CHARS]}"
        )

        client = build_gemini_client()
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_json_schema=_RESPONSE_SCHEMA,
                # See the matching comment in
                # apps.processing.providers.GeminiClassificationProvider
                # — this is direct extraction, not a reasoning task.
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        data = json.loads(response.text or "{}")

        results = []
        for key, label, is_required in INVOICE_SCHEMA:
            field = data.get(key) or {}
            value = str(field.get("value") or "").strip()
            confidence = float(field.get("confidence") or 0.0) if value else 0.0
            confidence = max(0.0, min(1.0, confidence))
            results.append(
                ExtractedFieldResult(
                    key=key,
                    label=label,
                    value=value,
                    confidence=confidence,
                    is_required=is_required,
                )
            )
        return results


def get_extraction_provider() -> ExtractionProvider:
    if settings.DOCUMENT_EXTRACTION_PROVIDER == "gemini":
        return GeminiExtractionProvider()
    return RegexInvoiceExtractionProvider()
