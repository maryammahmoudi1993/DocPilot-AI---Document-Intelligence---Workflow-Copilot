"""Pure pipeline-stage functions — no Celery, no database writes (the
caller, tasks.py, is responsible for persisting the mutated job and
appending to its stage_history). Each function either mutates the given
ProcessingJob's in-memory fields or raises a normalized
apps.processing.exceptions.ProcessingError subclass. Kept pure and
side-effect-free specifically so they're unit-testable without a
database or Celery — see apps/processing/tests/test_pipeline.py.
"""

import io

from django.conf import settings
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from apps.processing.exceptions import ValidationProcessingError
from apps.processing.models import ProcessingJob
from apps.processing.providers import ClassificationProvider, OCRProvider

PDF_CONTENT_TYPE = "application/pdf"


def stage_validate(job: ProcessingJob, file_bytes: bytes) -> None:
    """Only the PDF path has anything meaningful to validate here —
    Phase 3's upload-time validation already checked
    extension/MIME/magic bytes for every content type, so this stage's
    job is narrower: can pypdf actually open this specific file, and is
    it readable without a password?"""
    if job.document.content_type != PDF_CONTENT_TYPE:
        return

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            # An empty-password attempt is the standard way to
            # distinguish "encrypted with restrictions but no user
            # password" (common for permission-locked PDFs, effectively
            # readable) from "genuinely needs a password" — pypdf
            # returns 0 pages of success on `decrypt("")` for the latter.
            if not reader.decrypt(""):
                raise ValidationProcessingError(
                    "The PDF is password-protected.", code="password_protected_pdf"
                )
        else:
            # Force parsing beyond the header/xref — a truncated or
            # otherwise structurally broken PDF can open successfully
            # here and only fail once page content is actually read.
            _ = len(reader.pages)
    except ValidationProcessingError:
        raise
    except PdfReadError as exc:
        raise ValidationProcessingError(
            "The PDF file is corrupt or unreadable.", code="corrupt_file"
        ) from exc
    except Exception as exc:  # noqa: BLE001 - normalize any other pypdf parse failure the same way
        raise ValidationProcessingError(
            "The PDF file is corrupt or unreadable.", code="corrupt_file"
        ) from exc


def stage_extract_text(job: ProcessingJob, file_bytes: bytes) -> tuple[str, list[int]]:
    """Returns (digital_text, ocr_page_numbers) and sets
    job.total_pages/job.ocr_page_count. A page's extracted text shorter
    than settings.DOCUMENT_MIN_DIGITAL_TEXT_CHARS is treated as having
    no usable digital text layer (i.e. scanned) and its 1-based page
    number is included in ocr_page_numbers for stage_run_ocr to target."""
    content_type = job.document.content_type

    if content_type == PDF_CONTENT_TYPE:
        reader = PdfReader(io.BytesIO(file_bytes))
        job.total_pages = len(reader.pages)

        digital_texts: list[str] = []
        ocr_page_numbers: list[int] = []
        for index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if len(text) < settings.DOCUMENT_MIN_DIGITAL_TEXT_CHARS:
                ocr_page_numbers.append(index)
            else:
                digital_texts.append(text)

        job.ocr_page_count = len(ocr_page_numbers)
        return "\n".join(digital_texts), ocr_page_numbers

    if content_type.startswith("image/"):
        # No digital text layer to speak of — the whole image needs OCR.
        job.total_pages = 1
        job.ocr_page_count = 1
        return "", [1]

    # docx/xlsx/csv/txt/etc: no page-image concept, so OCR isn't
    # applicable. This phase's explicit scope is the PDF/image OCR
    # pipeline (see the Phase 4 prompt's backend task list) — other
    # content types complete with no extracted text rather than a fake
    # extraction result.
    job.total_pages = 1
    job.ocr_page_count = 0
    return "", []


def stage_run_ocr(
    job: ProcessingJob,
    file_bytes: bytes,
    digital_text: str,
    ocr_page_numbers: list[int],
    provider: OCRProvider,
) -> str:
    """Calls the OCR provider only for the pages stage_extract_text
    flagged — a fully digital PDF (ocr_page_numbers == []) never touches
    the provider at all, which is the whole point of routing OCR only
    to pages that need it."""
    if not ocr_page_numbers:
        return digital_text

    if job.document.content_type.startswith("image/"):
        ocr_parts = [provider.extract_text_from_image(image_bytes=file_bytes)]
    else:
        ocr_parts = [
            provider.extract_text_from_page(pdf_bytes=file_bytes, page_number=page_number)
            for page_number in ocr_page_numbers
        ]

    return "\n".join(part for part in [digital_text, *ocr_parts] if part)


def stage_classify(
    job: ProcessingJob, combined_text: str, provider: ClassificationProvider
) -> None:
    # Only a bounded sample is ever handed to the classifier — never the
    # full extracted text (keeps this stage's footprint small and
    # matches the "don't pass more than needed" spirit of the raw-text
    # retention rule on ProcessingJob.raw_text_excerpt).
    job.document_type = provider.classify(
        filename=job.document.filename, text_sample=combined_text[:2000]
    )


def stage_extract_fields(job: ProcessingJob, combined_text: str) -> None:
    """Delegates to apps.extraction (Phase 5) for invoice documents only
    — this phase's explicit schema scope (see
    apps/extraction/providers.py's INVOICE_SCHEMA). Other document types
    complete processing with no structured extraction rather than a
    fabricated one. Never raises: a provider/service failure here must
    not fail the whole processing job (the job's job is text
    extraction/OCR/classification; structured extraction has its own,
    separate review lifecycle)."""
    from apps.extraction.providers import get_extraction_provider
    from apps.extraction.services import build_extraction_for_job
    from apps.processing.models import DocumentType

    if job.document_type != DocumentType.INVOICE:
        return

    try:
        build_extraction_for_job(job, text=combined_text, provider=get_extraction_provider())
    except Exception:  # noqa: BLE001 - see docstring: extraction failure must not fail the job
        import logging

        logging.getLogger(__name__).exception(
            "extraction_stage_failed", extra={"job_id": str(job.id)}
        )
