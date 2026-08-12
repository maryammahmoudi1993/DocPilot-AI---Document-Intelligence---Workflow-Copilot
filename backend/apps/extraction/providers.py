"""Structured-extraction provider abstraction (project rule: mock
external providers at module boundaries). `RegexInvoiceExtractionProvider`
is a deterministic, no-network stand-in for a real document-AI/LLM
extraction call — it looks for `Label: value` style lines in the
combined OCR/digital text produced by apps.processing.pipeline. It is
intentionally simple: this phase's job is the review/correction/approval
*loop*, not extraction accuracy, and a regex provider keeps every test
in this app fast and deterministic (no paid provider calls)."""

import re
from dataclasses import dataclass
from typing import Protocol

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


def get_extraction_provider() -> ExtractionProvider:
    return RegexInvoiceExtractionProvider()
