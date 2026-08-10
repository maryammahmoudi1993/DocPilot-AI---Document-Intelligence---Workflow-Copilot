"""Processing-job business logic — kept out of views/tasks (non-negotiable
project rule) so scheduling/idempotency decisions are independently
unit-testable. See apps/documents/services.py's create_document, which
calls enqueue_processing after a successful upload commits.
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record_event
from apps.documents.models import Document
from apps.processing.models import TERMINAL_STAGES, ProcessingJob, ProcessingStage
from apps.processing.tasks import run_processing_pipeline


def get_latest_processing_job(*, document: Document) -> ProcessingJob | None:
    return ProcessingJob.objects.filter(document=document).order_by("-created_at").first()


def enqueue_processing(*, document: Document, correlation_id: str = "") -> ProcessingJob:
    """Idempotent: if an active (non-terminal) job already exists for
    this document, it's returned as-is rather than creating a duplicate
    — a duplicate upload-confirmation retry, a page double-submit, or
    any other accidental double-call is safe."""
    existing = (
        ProcessingJob.objects.filter(document=document)
        .exclude(stage__in=TERMINAL_STAGES)
        .order_by("-created_at")
        .first()
    )
    if existing is not None:
        return existing

    job = ProcessingJob.objects.create(
        document=document,
        workspace=document.workspace,
        correlation_id=correlation_id or str(uuid.uuid4()),
    )
    # Only schedule the task once the row is actually committed — the
    # worker (a separate process) querying for this job.id before the
    # transaction commits would otherwise get DoesNotExist.
    transaction.on_commit(lambda: run_processing_pipeline.delay(str(job.id)))
    return job


def retry_processing(*, document: Document, actor) -> ProcessingJob:
    latest = get_latest_processing_job(document=document)
    if latest is None or latest.stage != ProcessingStage.FAILED or not latest.is_retryable:
        raise ValidationError({"stage": "This document has no retryable failed processing job."})

    job = ProcessingJob.objects.create(
        document=document,
        workspace=document.workspace,
        correlation_id=str(uuid.uuid4()),
    )
    record_event(
        event_type="document.processing_retried",
        actor=actor,
        workspace=document.workspace,
        metadata={"document_id": str(document.id), "job_id": str(job.id)},
    )
    transaction.on_commit(lambda: run_processing_pipeline.delay(str(job.id)))
    return job
