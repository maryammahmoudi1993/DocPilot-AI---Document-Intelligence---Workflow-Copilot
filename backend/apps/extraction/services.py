"""Business logic for structured extraction, correction, validation, and
review transitions — kept out of views/serializers/tasks per the
project's non-negotiable rule. Two entry points matter most:

- `build_extraction_for_job` — called from the processing pipeline once
  a job classifies as an invoice; idempotent (see its docstring).
- `correct_field` / `transition_status` — called from the review API;
  both enforce optimistic locking via `expected_version`.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.extraction.exceptions import (
    ExtractionLockedError,
    InvalidTransitionError,
    StaleVersionError,
)
from apps.extraction.models import (
    DocumentExtraction,
    ExtractedField,
    ExtractionStatus,
    FieldCorrection,
    ValidationIssue,
    ValidationSeverity,
)
from apps.extraction.providers import ExtractionProvider

if TYPE_CHECKING:
    from apps.processing.models import ProcessingJob

MONEY_FIELDS = {"subtotal", "tax", "discount", "total"}
DATE_FIELDS = {"invoice_date", "due_date"}

# Only PENDING_REVIEW -> {APPROVED, REJECTED} and REJECTED -> PENDING_REVIEW
# (send back for another look) are allowed. APPROVED is terminal — once
# approved, the extraction is locked (see ExtractionLockedError).
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    ExtractionStatus.PENDING_REVIEW: {ExtractionStatus.APPROVED, ExtractionStatus.REJECTED},
    ExtractionStatus.REJECTED: {ExtractionStatus.PENDING_REVIEW},
    ExtractionStatus.APPROVED: set(),
}


def _normalize_money(raw: str) -> str | None:
    cleaned = raw.replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return str(Decimal(cleaned).quantize(Decimal("0.01")))
    except InvalidOperation:
        return None


def _normalize_date(raw: str) -> str | None:
    cleaned = raw.strip()
    if not cleaned:
        return None
    try:
        return datetime.strptime(cleaned, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def normalize_value(key: str, raw: str) -> str | None:
    if key in MONEY_FIELDS:
        return _normalize_money(raw)
    if key in DATE_FIELDS:
        return _normalize_date(raw)
    return raw.strip() or None


@transaction.atomic
def build_extraction_for_job(
    job: "ProcessingJob", *, text: str, provider: ExtractionProvider
) -> DocumentExtraction | None:
    """Creates (or, on a duplicate/retried task run, reuses) the
    DocumentExtraction for `job.document`. Idempotent: if an extraction
    already exists and a reviewer has moved it past PENDING_REVIEW (or
    made any correction), re-running extraction never overwrites their
    work — it's a no-op. This is what makes duplicate/retried Celery
    task execution safe for this stage."""
    extraction, created = DocumentExtraction.objects.get_or_create(
        document=job.document,
        defaults={"workspace": job.workspace, "document_type": job.document_type or ""},
    )
    if not created and (
        extraction.status != ExtractionStatus.PENDING_REVIEW
        or FieldCorrection.objects.filter(field__extraction=extraction).exists()
    ):
        return extraction

    results = provider.extract(text=text)
    confidences: list[float] = []
    for result in results:
        normalized = normalize_value(result.key, result.value) if result.value else None
        ExtractedField.objects.update_or_create(
            extraction=extraction,
            key=result.key,
            defaults={
                "label": result.label,
                "display_value": result.value,
                "normalized_value": normalized or "",
                "confidence": result.confidence,
                "is_required": result.is_required,
            },
        )
        confidences.append(result.confidence)

    extraction.overall_confidence = sum(confidences) / len(confidences) if confidences else None
    extraction.save(update_fields=["overall_confidence", "updated_at"])
    run_validations(extraction)
    return extraction


def run_validations(extraction: DocumentExtraction) -> list[ValidationIssue]:
    """Regenerates every auto-detected validation issue for this
    extraction from scratch — safe to call any number of times (after
    extraction, after every correction) since it always reflects current
    field state rather than accumulating stale issues."""
    ValidationIssue.objects.filter(extraction=extraction).delete()
    fields = {f.key: f for f in extraction.fields.all()}
    issues: list[ValidationIssue] = []

    def add(code: str, message: str, severity: str, field: ExtractedField | None = None) -> None:
        issues.append(
            ValidationIssue(
                extraction=extraction, field=field, code=code, message=message, severity=severity
            )
        )

    for field in fields.values():
        if field.is_required and not field.normalized_value:
            add(
                "required_field_missing",
                f"{field.label} is required but missing.",
                ValidationSeverity.ERROR,
                field,
            )

    invoice_date_field = fields.get("invoice_date")
    due_date_field = fields.get("due_date")
    if (
        invoice_date_field
        and due_date_field
        and invoice_date_field.normalized_value
        and due_date_field.normalized_value
    ):
        try:
            invoice_date = date.fromisoformat(invoice_date_field.normalized_value)
            due_date = date.fromisoformat(due_date_field.normalized_value)
            if due_date < invoice_date:
                add(
                    "due_date_before_invoice_date",
                    "Due date cannot be before the invoice date.",
                    ValidationSeverity.ERROR,
                    due_date_field,
                )
        except ValueError:
            pass

    subtotal_field = fields.get("subtotal")
    tax_field = fields.get("tax")
    discount_field = fields.get("discount")
    total_field = fields.get("total")
    if (
        total_field
        and total_field.normalized_value
        and subtotal_field
        and subtotal_field.normalized_value
    ):
        try:
            subtotal = Decimal(subtotal_field.normalized_value)
            tax = (
                Decimal(tax_field.normalized_value)
                if tax_field and tax_field.normalized_value
                else Decimal("0")
            )
            discount = (
                Decimal(discount_field.normalized_value)
                if discount_field and discount_field.normalized_value
                else Decimal("0")
            )
            total = Decimal(total_field.normalized_value)
            if (subtotal + tax - discount).quantize(Decimal("0.01")) != total.quantize(
                Decimal("0.01")
            ):
                add(
                    "arithmetic_mismatch",
                    "Subtotal + tax − discount does not equal the total.",
                    ValidationSeverity.ERROR,
                    total_field,
                )
        except InvalidOperation:
            pass

    for field in fields.values():
        if field.confidence is not None and 0 < field.confidence < 0.5:
            add(
                "low_confidence",
                f"{field.label} was extracted with low confidence and should be checked.",
                ValidationSeverity.WARNING,
                field,
            )

    ValidationIssue.objects.bulk_create(issues)
    return issues


def _check_version(extraction: DocumentExtraction, expected_version: int) -> None:
    if extraction.version != expected_version:
        raise StaleVersionError()


@transaction.atomic
def correct_field(
    *, field: ExtractedField, user, value: str, reason: str, expected_version: int
) -> ExtractedField:
    extraction = DocumentExtraction.objects.select_for_update().get(id=field.extraction_id)
    if extraction.status != ExtractionStatus.PENDING_REVIEW:
        raise ExtractionLockedError()
    _check_version(extraction, expected_version)

    before = field.display_value
    normalized = normalize_value(field.key, value) if value else None
    field.display_value = value
    field.normalized_value = normalized or ""
    field.save(update_fields=["display_value", "normalized_value", "updated_at"])

    FieldCorrection.objects.create(
        field=field, before_value=before, after_value=value, reason=reason, corrected_by=user
    )

    extraction.version += 1
    extraction.reviewed_by = user
    extraction.reviewed_at = timezone.now()
    extraction.save(update_fields=["version", "reviewed_by", "reviewed_at", "updated_at"])
    run_validations(extraction)

    record_event(
        event_type="extraction.field_corrected",
        actor=user,
        workspace=extraction.workspace,
        metadata={"extraction_id": str(extraction.id), "field_key": field.key},
    )
    return field


@dataclass(frozen=True)
class TransitionResult:
    extraction: DocumentExtraction


@transaction.atomic
def transition_status(
    *, extraction: DocumentExtraction, new_status: str, user, expected_version: int
) -> DocumentExtraction:
    extraction = DocumentExtraction.objects.select_for_update().get(id=extraction.id)
    _check_version(extraction, expected_version)

    allowed = _ALLOWED_TRANSITIONS.get(extraction.status, set())
    if new_status not in allowed:
        raise InvalidTransitionError(f"Cannot move from {extraction.status} to {new_status}.")

    if new_status == ExtractionStatus.APPROVED:
        blocking = extraction.issues.filter(severity=ValidationSeverity.ERROR).exists()
        if blocking:
            raise InvalidTransitionError(
                "Cannot approve while unresolved validation errors remain."
            )
        extraction.approved_by = user
        extraction.approved_at = timezone.now()

    extraction.status = new_status
    extraction.version += 1
    extraction.reviewed_by = user
    extraction.reviewed_at = timezone.now()
    extraction.save()

    record_event(
        event_type=f"extraction.{new_status}",
        actor=user,
        workspace=extraction.workspace,
        metadata={"extraction_id": str(extraction.id)},
    )
    return extraction
