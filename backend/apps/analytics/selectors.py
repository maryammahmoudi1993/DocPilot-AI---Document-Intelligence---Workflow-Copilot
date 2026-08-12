"""Read-only aggregation queries over existing apps' data — this app
owns no models of its own. Every function is workspace-scoped and
returns real numbers computed from real rows; nothing here is a mock or
placeholder value (see the project's honest-metrics rule). A metric
whose meaning could be misread as a verified accuracy/SLA claim is
explicitly labeled `is_illustrative` in its response shape (see
serializers.py) rather than presented as fact.
"""

from datetime import date, timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.approvals.models import ApprovalRequest, ApprovalStatus
from apps.documents.models import Document
from apps.extraction.models import DocumentExtraction, ExtractionStatus, ValidationSeverity
from apps.processing.models import ProcessingJob, ProcessingStage
from apps.workflows.models import WorkflowRun, WorkflowRunStatus


def dashboard_summary(*, workspace_id) -> dict:
    documents_qs = Document.objects.filter(workspace_id=workspace_id)
    jobs_qs = ProcessingJob.objects.filter(workspace_id=workspace_id)
    approvals_qs = ApprovalRequest.objects.filter(workspace_id=workspace_id)

    return {
        "total_documents": documents_qs.count(),
        "documents_processing": jobs_qs.exclude(
            stage__in=[ProcessingStage.COMPLETED, ProcessingStage.FAILED]
        ).count(),
        "documents_needing_review": DocumentExtraction.objects.filter(
            workspace_id=workspace_id, status=ExtractionStatus.PENDING_REVIEW
        ).count(),
        "pending_approvals": approvals_qs.filter(status=ApprovalStatus.PENDING).count(),
        "failed_jobs": jobs_qs.filter(stage=ProcessingStage.FAILED).count(),
    }


def processing_trends(*, workspace_id, since: date, until: date) -> list[dict]:
    """One row per calendar day in [since, until] — days with zero
    activity are included with zero counts so a chart doesn't silently
    skip them."""
    rows = (
        ProcessingJob.objects.filter(
            workspace_id=workspace_id, created_at__date__gte=since, created_at__date__lte=until
        )
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            completed=Count("id", filter=Q(stage=ProcessingStage.COMPLETED)),
            failed=Count("id", filter=Q(stage=ProcessingStage.FAILED)),
            total=Count("id"),
        )
        .order_by("day")
    )
    by_day = {row["day"]: row for row in rows}

    result = []
    current = since
    while current <= until:
        row = by_day.get(current)
        result.append(
            {
                "date": current.isoformat(),
                "total": row["total"] if row else 0,
                "completed": row["completed"] if row else 0,
                "failed": row["failed"] if row else 0,
            }
        )
        current += timedelta(days=1)
    return result


def document_type_counts(*, workspace_id) -> list[dict]:
    rows = (
        ProcessingJob.objects.filter(workspace_id=workspace_id)
        .values("document_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return [{"document_type": row["document_type"], "count": row["count"]} for row in rows]


def extraction_accuracy_metrics(*, workspace_id) -> dict:
    """`average_confidence` is the mean of each extraction's own
    model-reported confidence score — a real, computed number, but
    explicitly labeled illustrative (see serializers.py) because no
    ground-truth-labeled dataset exists in this portfolio project to
    validate it against."""
    extractions = DocumentExtraction.objects.filter(workspace_id=workspace_id)
    average_confidence = extractions.aggregate(avg=Avg("overall_confidence"))["avg"]
    total = extractions.count()
    with_validation_issues = (
        extractions.filter(issues__severity=ValidationSeverity.ERROR).distinct().count()
    )

    return {
        "average_confidence": average_confidence,
        "total_extractions": total,
        "extractions_with_validation_errors": with_validation_issues,
        "is_illustrative": True,
    }


def review_rate_metrics(*, workspace_id) -> dict:
    extractions = DocumentExtraction.objects.filter(workspace_id=workspace_id)
    total = extractions.count()
    reviewed = extractions.filter(reviewed_at__isnull=False).count()
    return {
        "total_extractions": total,
        "reviewed_count": reviewed,
        "review_rate": (reviewed / total) if total else None,
    }


def workflow_success_metrics(*, workspace_id) -> dict:
    runs = WorkflowRun.objects.filter(workspace_id=workspace_id, is_test_run=False)
    total = runs.count()
    succeeded = runs.filter(status=WorkflowRunStatus.COMPLETED).count()
    failed = runs.filter(status=WorkflowRunStatus.FAILED).count()
    return {
        "total_runs": total,
        "succeeded": succeeded,
        "failed": failed,
        "success_rate": (succeeded / total) if total else None,
    }


def average_approval_duration_seconds(*, workspace_id) -> float | None:
    decided = ApprovalRequest.objects.filter(
        workspace_id=workspace_id, decided_at__isnull=False
    ).annotate(
        duration=ExpressionWrapper(F("decided_at") - F("created_at"), output_field=DurationField())
    )
    result = decided.aggregate(avg=Avg("duration"))["avg"]
    return result.total_seconds() if result else None


def default_date_range(days: int = 30) -> tuple[date, date]:
    until = timezone.now().date()
    since = until - timedelta(days=days - 1)
    return since, until
