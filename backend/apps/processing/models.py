import uuid

from django.db import models


class ProcessingStage(models.TextChoices):
    """Explicit pipeline stages (see apps/processing/tasks.py for the
    orchestrator that walks a job through these in order).

    `EXTRACTING_FIELDS`, `VALIDATING_EXTRACTION`, and `SCORING_CONFIDENCE`
    are placeholders in this phase — Phase 5 owns the real structured-
    extraction models (`DocumentExtraction`/`ExtractedField`) and business
    validation; until that phase lands, these stages transition through
    without persisting fabricated data (see pipeline.py). Likewise
    `INDEXING` is a placeholder for Phase 6's pgvector chunk indexing.
    """

    QUEUED = "queued", "Queued"
    VALIDATING = "validating", "Validating"
    EXTRACTING_TEXT = "extracting_text", "Extracting text"
    RUNNING_OCR = "running_ocr", "Running OCR"
    CLASSIFYING = "classifying", "Classifying"
    EXTRACTING_FIELDS = "extracting_fields", "Extracting structured data"
    VALIDATING_EXTRACTION = "validating_extraction", "Validating extraction"
    SCORING_CONFIDENCE = "scoring_confidence", "Scoring confidence"
    INDEXING = "indexing", "Indexing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


# Order the orchestrator walks stages in (see tasks.py). Not stored
# anywhere — derived here once so the task and any code inspecting
# progress share one definition of "what's next".
STAGE_ORDER = [
    ProcessingStage.QUEUED,
    ProcessingStage.VALIDATING,
    ProcessingStage.EXTRACTING_TEXT,
    ProcessingStage.RUNNING_OCR,
    ProcessingStage.CLASSIFYING,
    ProcessingStage.EXTRACTING_FIELDS,
    ProcessingStage.VALIDATING_EXTRACTION,
    ProcessingStage.SCORING_CONFIDENCE,
    ProcessingStage.INDEXING,
    ProcessingStage.COMPLETED,
]

TERMINAL_STAGES = {ProcessingStage.COMPLETED, ProcessingStage.FAILED}


class DocumentType(models.TextChoices):
    """Classification result — a deterministic keyword heuristic in this
    phase (see apps/processing/providers.py), not an LLM call. Swappable
    behind the same ClassificationProvider interface later without
    touching the pipeline or this model."""

    INVOICE = "invoice", "Invoice"
    CONTRACT = "contract", "Contract"
    RECEIPT = "receipt", "Receipt"
    REPORT = "report", "Report"
    POLICY = "policy", "Policy"
    FORM = "form", "Form"
    UNKNOWN = "unknown", "Unknown"


class ProcessingJob(models.Model):
    """One attempt at running a `Document` through the async processing
    pipeline. A document can have more than one job over its lifetime
    (e.g. a user-initiated retry after a failure creates a fresh job
    rather than mutating the failed one, keeping history) — but the
    service layer (see services.py) never lets two *active* (non-
    terminal) jobs exist for the same document at once, which is what
    makes duplicate processing requests safe.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        "documents.Document", on_delete=models.CASCADE, related_name="processing_jobs"
    )
    # Denormalized from document.workspace — avoids a join for the
    # workspace-scoped list/permission query pattern every other app in
    # this project already uses (see Document.Meta.indexes for the same
    # rationale).
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="processing_jobs"
    )
    stage = models.CharField(
        max_length=32, choices=ProcessingStage.choices, default=ProcessingStage.QUEUED
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    is_retryable = models.BooleanField(default=False)
    # Stable, safe-to-display codes only (e.g. "corrupt_file",
    # "password_protected_pdf") — never a raw exception message or
    # traceback. See apps/processing/exceptions.py. `null=True` (rather
    # than the usual Django CharField convention of blank="" as the only
    # "empty" sentinel) is deliberate here: None unambiguously means "no
    # error has happened yet", distinct from an empty string that could
    # otherwise be mistaken for a (nonsensical) empty error code.
    error_code = models.CharField(max_length=64, null=True, blank=True)  # noqa: DJ001
    error_message = models.CharField(max_length=500, null=True, blank=True)  # noqa: DJ001

    # Same rationale as error_code/error_message above: None means
    # "classification hasn't run yet", not "classified as nothing".
    document_type = models.CharField(  # noqa: DJ001
        max_length=16, choices=DocumentType.choices, null=True, blank=True
    )
    total_pages = models.PositiveIntegerField(null=True, blank=True)
    ocr_page_count = models.PositiveIntegerField(default=0)
    # Bounded excerpt only — the *safe retention rule* for this phase is
    # that full extracted/OCR'd text is never persisted here at all.
    # Phase 5's DocumentExtraction model is where real, retained
    # structured content will live under its own review/redaction rules;
    # this field exists only so a developer can sanity-check what the
    # pipeline saw, not as a durable content store.
    raw_text_excerpt = models.CharField(max_length=2000, blank=True)

    # Propagated from the HTTP request that triggered this job (or
    # generated fresh for a system-triggered one) so worker-side log
    # lines can be correlated back to the request that caused them — see
    # common.logging.CorrelationIdFilter and tasks.py.
    correlation_id = models.CharField(max_length=64, blank=True)

    # Append-only list of {stage, status, detail, at} dicts — the
    # "execution log" for this job. `detail` is always a short, safe
    # string (counts, stage names, error codes) — never raw document
    # content (see the redaction rule on raw_text_excerpt above).
    stage_history = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["document", "-created_at"]),
            models.Index(fields=["workspace", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ProcessingJob({self.document_id}, {self.stage})"

    @property
    def is_active(self) -> bool:
        return self.stage not in TERMINAL_STAGES
