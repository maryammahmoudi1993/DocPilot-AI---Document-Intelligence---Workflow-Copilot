"""Structured extraction and human-review models for one invoice's
extracted data. A `DocumentExtraction` is created once a `ProcessingJob`
reaches the (Phase 5-owned) extracting_fields stage — see
apps/processing/pipeline.py's stage_extract_fields, which calls into
apps/extraction/services.py rather than writing these models directly
from a Celery task (business logic stays out of task functions)."""

import uuid

from django.conf import settings
from django.db import models


class ExtractionStatus(models.TextChoices):
    PENDING_REVIEW = "pending_review", "Pending review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class ValidationSeverity(models.TextChoices):
    ERROR = "error", "Error"
    WARNING = "warning", "Warning"


class DocumentExtraction(models.Model):
    """One per `Document` (invoices only in this phase's schema — see
    services.INVOICE_SCHEMA). `version` is an optimistic-concurrency
    counter: every correction or status transition must supply the
    version it read and bumps it by one on success, so two reviewers
    racing on the same extraction get one winner and one stale-version
    rejection rather than a silent overwrite (see services.py)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(
        "documents.Document", on_delete=models.CASCADE, related_name="extraction"
    )
    # Denormalized from document.workspace for the same reason as every
    # other workspace-scoped model in this project (see
    # ProcessingJob.workspace).
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="extractions"
    )
    document_type = models.CharField(max_length=16)
    status = models.CharField(
        max_length=16, choices=ExtractionStatus.choices, default=ExtractionStatus.PENDING_REVIEW
    )
    version = models.PositiveIntegerField(default=1)
    # Mean of field-level confidences at extraction time — display-only,
    # never used to gate approval by itself (validation issues are what
    # gate approval; see services.transition_status).
    overall_confidence = models.FloatField(null=True, blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "status", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"DocumentExtraction({self.document_id}, {self.status})"


class ExtractedField(models.Model):
    """One structured field on an extraction (e.g. `total`,
    `invoice_number`). `normalized_value` is what business validation
    and downstream consumers read (e.g. a decimal string with no
    currency symbol or thousands separator); `display_value` is what the
    provider originally produced, kept so a reviewer can see what
    changed after a correction. Source page/bounding box are optional —
    only populated when the provider/OCR pipeline supplies coordinates,
    so the review UI can degrade gracefully without them."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    extraction = models.ForeignKey(
        DocumentExtraction, on_delete=models.CASCADE, related_name="fields"
    )
    key = models.CharField(max_length=64)
    label = models.CharField(max_length=128)
    display_value = models.CharField(max_length=500, blank=True)
    normalized_value = models.CharField(max_length=500, blank=True)  # noqa: DJ001
    confidence = models.FloatField(null=True, blank=True)
    is_required = models.BooleanField(default=False)
    page_number = models.PositiveIntegerField(null=True, blank=True)
    # {"x": float, "y": float, "width": float, "height": float} in
    # normalized (0..1) page coordinates, or null when unavailable.
    bounding_box = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["extraction", "key"])]
        constraints = [
            models.UniqueConstraint(
                fields=["extraction", "key"], name="unique_field_per_extraction"
            )
        ]
        ordering = ["key"]

    def __str__(self) -> str:
        return f"ExtractedField({self.extraction_id}, {self.key})"


class ValidationIssue(models.Model):
    """A business-rule or required-field violation on an extraction.
    Regenerated (not accumulated) each time services.run_validations
    runs — see that function's idempotency note. `error`-severity issues
    block approval; `warning`-severity issues do not (see
    services.transition_status)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    extraction = models.ForeignKey(
        DocumentExtraction, on_delete=models.CASCADE, related_name="issues"
    )
    field = models.ForeignKey(
        ExtractedField, null=True, blank=True, on_delete=models.CASCADE, related_name="issues"
    )
    code = models.CharField(max_length=64)
    message = models.CharField(max_length=255)
    severity = models.CharField(max_length=16, choices=ValidationSeverity.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["extraction", "severity"])]
        ordering = ["severity", "code"]

    def __str__(self) -> str:
        return f"ValidationIssue({self.extraction_id}, {self.code})"


class FieldCorrection(models.Model):
    """Immutable audit record of one reviewer edit to one field. Never
    updated or deleted — the correction trail is append-only, matching
    the project's broader audit-event conventions (see apps.audit)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    field = models.ForeignKey(ExtractedField, on_delete=models.CASCADE, related_name="corrections")
    before_value = models.CharField(max_length=500, blank=True)
    after_value = models.CharField(max_length=500, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    corrected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["field", "-corrected_at"])]
        ordering = ["-corrected_at"]

    def __str__(self) -> str:
        return f"FieldCorrection({self.field_id}, {self.corrected_at})"
