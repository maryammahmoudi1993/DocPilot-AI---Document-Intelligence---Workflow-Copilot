"""Celery orchestrator for the document-processing pipeline. One task,
`run_processing_pipeline`, walks a ProcessingJob through every stage in
apps.processing.models.STAGE_ORDER, delegating the actual work per
stage to the pure functions in pipeline.py and persisting
progress/results after each one so the status endpoint (views.py) is
always reading real, current state — never a guess.

Idempotency: a job already in a terminal stage (COMPLETED/FAILED) is a
safe no-op — covers both an accidental duplicate `.delay()` call and
Celery's own at-least-once delivery redelivering a task after it already
finished. A missing job id (e.g. the row was deleted) is also a safe
no-op, not a crash.
"""

import logging

from celery import shared_task
from django.utils import timezone

from apps.documents.storage import get_storage_backend
from apps.processing import pipeline
from apps.processing.exceptions import ProcessingError
from apps.processing.models import TERMINAL_STAGES, ProcessingJob, ProcessingStage
from apps.processing.providers import get_classification_provider, get_ocr_provider
from common.logging import correlation_id_var

logger = logging.getLogger(__name__)

# Total attempts (first try + retries) for a retryable failure before the
# job is given up on as FAILED. Small and fixed rather than configurable
# — this is a portfolio-scale pipeline, not a tunable production queue.
MAX_ATTEMPTS = 3


def _append_history(job: ProcessingJob, stage: str, status: str, detail: str = "") -> None:
    # `detail` must stay short and safe (a count, a stage name, an error
    # code) — never raw document/OCR content. See ProcessingJob's
    # raw_text_excerpt docstring for the corresponding retention rule.
    job.stage_history = [
        *job.stage_history,
        {"stage": stage, "status": status, "detail": detail, "at": timezone.now().isoformat()},
    ]


@shared_task(bind=True, max_retries=MAX_ATTEMPTS - 1)
def run_processing_pipeline(self, job_id: str) -> None:  # noqa: ANN001 - Celery binds `self`
    try:
        job = ProcessingJob.objects.select_related("document").get(id=job_id)
    except ProcessingJob.DoesNotExist:
        logger.warning("processing_job_not_found", extra={"job_id": job_id})
        return

    if job.stage in TERMINAL_STAGES:
        return

    token = correlation_id_var.set(job.correlation_id or "unknown")
    try:
        _run(self, job)
    finally:
        correlation_id_var.reset(token)


def _run(task, job: ProcessingJob) -> None:  # noqa: ANN001
    job.attempt_count += 1
    if job.started_at is None:
        job.started_at = timezone.now()
    job.save(update_fields=["attempt_count", "started_at"])

    storage = get_storage_backend()
    try:
        file_bytes = storage.download(key=job.document.storage_key)

        job.stage = ProcessingStage.VALIDATING
        _append_history(job, job.stage, "started")
        pipeline.stage_validate(job, file_bytes)
        _append_history(job, job.stage, "completed")

        job.stage = ProcessingStage.EXTRACTING_TEXT
        _append_history(job, job.stage, "started")
        digital_text, ocr_page_numbers = pipeline.stage_extract_text(job, file_bytes)
        extract_detail = f"{job.total_pages} page(s), {len(ocr_page_numbers)} need OCR"
        _append_history(job, job.stage, "completed", detail=extract_detail)

        job.stage = ProcessingStage.RUNNING_OCR
        _append_history(job, job.stage, "started" if ocr_page_numbers else "skipped")
        # Computed once, page-attributed, and reused for both the
        # combined text below (classification/extraction) and indexing
        # further down — deliberately not calling stage_run_ocr here as
        # well, which would call the OCR provider a second time for the
        # same pages (real cost against a real OCR provider).
        page_texts = pipeline.build_page_texts(
            job, file_bytes, ocr_page_numbers, get_ocr_provider()
        )
        combined_text = "\n".join(text for _, text in page_texts)
        if ocr_page_numbers:
            ocr_detail = f"{len(ocr_page_numbers)} page(s) OCR'd"
            _append_history(job, job.stage, "completed", detail=ocr_detail)

        job.stage = ProcessingStage.CLASSIFYING
        _append_history(job, job.stage, "started")
        pipeline.stage_classify(job, combined_text, get_classification_provider())
        _append_history(job, job.stage, "completed", detail=str(job.document_type))

        # Safe retention rule: only a bounded excerpt is ever persisted,
        # never the full extracted/OCR'd text — see ProcessingJob's
        # raw_text_excerpt docstring.
        job.raw_text_excerpt = combined_text[:2000]

        job.stage = ProcessingStage.EXTRACTING_FIELDS
        _append_history(job, job.stage, "started")
        pipeline.stage_extract_fields(job, combined_text)
        _append_history(job, job.stage, "completed")

        # Business validation and confidence scoring both run as part of
        # stage_extract_fields (see apps.extraction.services) — these two
        # stages exist for visible progress reporting, not separate work.
        job.stage = ProcessingStage.VALIDATING_EXTRACTION
        _append_history(job, job.stage, "completed", detail="performed within extracting_fields")
        job.stage = ProcessingStage.SCORING_CONFIDENCE
        _append_history(job, job.stage, "completed", detail="performed within extracting_fields")

        job.stage = ProcessingStage.INDEXING
        _append_history(job, job.stage, "started")
        chunk_count = pipeline.stage_index(job, page_texts)
        _append_history(job, job.stage, "completed", detail=f"{chunk_count} chunk(s)")

        job.stage = ProcessingStage.COMPLETED
        job.completed_at = timezone.now()
        _append_history(job, job.stage, "completed")
        job.save()

    except ProcessingError as exc:
        job.error_code = exc.code
        job.error_message = str(exc)
        job.is_retryable = exc.retryable
        _append_history(job, job.stage, "failed", detail=exc.code)

        if exc.retryable and task.request.retries < MAX_ATTEMPTS - 1:
            job.save()
            # Exponential backoff (1s, 2s, 4s, ...) — small and bounded
            # since MAX_ATTEMPTS is small; a real production queue would
            # tune this against the specific provider's rate limits.
            raise task.retry(exc=exc, countdown=2**task.request.retries) from exc

        job.stage = ProcessingStage.FAILED
        job.save()
        logger.warning(
            "processing_job_failed",
            extra={"job_id": str(job.id), "code": exc.code, "correlation_id": job.correlation_id},
        )

    except Exception:  # noqa: BLE001 - last-resort safety net; never leak internals to the job record
        job.error_code = "internal_error"
        job.error_message = "An unexpected error occurred while processing this document."
        job.is_retryable = False
        job.stage = ProcessingStage.FAILED
        _append_history(job, job.stage, "failed", detail="internal_error")
        job.save()
        logger.exception("processing_job_unexpected_error", extra={"job_id": str(job.id)})
