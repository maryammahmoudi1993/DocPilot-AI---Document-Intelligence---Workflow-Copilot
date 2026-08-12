from datetime import timedelta

import pytest
from django.utils import timezone

from apps.analytics import selectors
from apps.approvals.models import ApprovalStatus
from apps.extraction.models import ExtractionStatus
from apps.processing.models import ProcessingStage
from apps.workflows.models import (
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowVersion,
    WorkflowVersionStatus,
)
from tests.factories import (
    ApprovalRequestFactory,
    DocumentExtractionFactory,
    ProcessingJobFactory,
    WorkflowFactory,
    WorkspaceFactory,
)


@pytest.mark.django_db
class TestDashboardSummary:
    def test_counts_are_scoped_to_the_workspace(self):
        workspace = WorkspaceFactory()
        other = WorkspaceFactory()
        ProcessingJobFactory(
            document__workspace=workspace, workspace=workspace, stage=ProcessingStage.QUEUED
        )
        ProcessingJobFactory(
            document__workspace=other, workspace=other, stage=ProcessingStage.QUEUED
        )
        ApprovalRequestFactory(workspace=workspace, status=ApprovalStatus.PENDING)

        summary = selectors.dashboard_summary(workspace_id=workspace.id)

        assert summary["total_documents"] == 1
        assert summary["documents_processing"] == 1
        assert summary["pending_approvals"] == 1

    def test_counts_pending_review_extractions(self):
        workspace = WorkspaceFactory()
        DocumentExtractionFactory(workspace=workspace, status=ExtractionStatus.PENDING_REVIEW)
        DocumentExtractionFactory(workspace=workspace, status=ExtractionStatus.APPROVED)

        summary = selectors.dashboard_summary(workspace_id=workspace.id)

        assert summary["documents_needing_review"] == 1


@pytest.mark.django_db
class TestProcessingTrends:
    def test_includes_zero_activity_days(self):
        workspace = WorkspaceFactory()
        today = timezone.now().date()

        trends = selectors.processing_trends(
            workspace_id=workspace.id, since=today - timedelta(days=2), until=today
        )

        assert len(trends) == 3
        assert all(point["total"] == 0 for point in trends)

    def test_counts_completed_and_failed_jobs_on_their_creation_day(self):
        workspace = WorkspaceFactory()
        today = timezone.now().date()
        ProcessingJobFactory(
            document__workspace=workspace, workspace=workspace, stage=ProcessingStage.COMPLETED
        )
        ProcessingJobFactory(
            document__workspace=workspace, workspace=workspace, stage=ProcessingStage.FAILED
        )

        trends = selectors.processing_trends(workspace_id=workspace.id, since=today, until=today)

        assert trends[0]["total"] == 2
        assert trends[0]["completed"] == 1
        assert trends[0]["failed"] == 1


@pytest.mark.django_db
def test_document_type_counts_groups_by_type():
    workspace = WorkspaceFactory()
    ProcessingJobFactory(
        document__workspace=workspace, workspace=workspace, document_type="invoice"
    )
    ProcessingJobFactory(
        document__workspace=workspace, workspace=workspace, document_type="invoice"
    )
    ProcessingJobFactory(
        document__workspace=workspace, workspace=workspace, document_type="contract"
    )

    counts = selectors.document_type_counts(workspace_id=workspace.id)

    by_type = {row["document_type"]: row["count"] for row in counts}
    assert by_type["invoice"] == 2
    assert by_type["contract"] == 1


@pytest.mark.django_db
class TestExtractionAccuracyMetrics:
    def test_is_always_labeled_illustrative(self):
        workspace = WorkspaceFactory()

        metrics = selectors.extraction_accuracy_metrics(workspace_id=workspace.id)

        assert metrics["is_illustrative"] is True

    def test_averages_real_confidence_scores(self):
        workspace = WorkspaceFactory()
        DocumentExtractionFactory(workspace=workspace, overall_confidence=0.8)
        DocumentExtractionFactory(workspace=workspace, overall_confidence=0.4)

        metrics = selectors.extraction_accuracy_metrics(workspace_id=workspace.id)

        assert metrics["average_confidence"] == pytest.approx(0.6)
        assert metrics["total_extractions"] == 2


@pytest.mark.django_db
def test_review_rate_metrics_computes_reviewed_fraction():
    workspace = WorkspaceFactory()
    DocumentExtractionFactory(workspace=workspace, reviewed_at=timezone.now())
    DocumentExtractionFactory(workspace=workspace, reviewed_at=None)

    metrics = selectors.review_rate_metrics(workspace_id=workspace.id)

    assert metrics["total_extractions"] == 2
    assert metrics["reviewed_count"] == 1
    assert metrics["review_rate"] == pytest.approx(0.5)


@pytest.mark.django_db
def test_review_rate_metrics_is_none_with_no_extractions():
    workspace = WorkspaceFactory()

    metrics = selectors.review_rate_metrics(workspace_id=workspace.id)

    assert metrics["review_rate"] is None


def _make_run(workspace, status):
    workflow = WorkflowFactory(workspace=workspace)
    version = WorkflowVersion.objects.create(
        workflow=workflow, version_number=1, status=WorkflowVersionStatus.ACTIVE
    )
    return WorkflowRun.objects.create(
        workflow=workflow, version=version, workspace=workspace, status=status
    )


@pytest.mark.django_db
def test_workflow_success_metrics_computes_success_rate():
    workspace = WorkspaceFactory()
    _make_run(workspace, WorkflowRunStatus.COMPLETED)
    _make_run(workspace, WorkflowRunStatus.COMPLETED)
    _make_run(workspace, WorkflowRunStatus.FAILED)

    metrics = selectors.workflow_success_metrics(workspace_id=workspace.id)

    assert metrics["total_runs"] == 3
    assert metrics["succeeded"] == 2
    assert metrics["failed"] == 1
    assert metrics["success_rate"] == pytest.approx(2 / 3)


@pytest.mark.django_db
def test_average_approval_duration_only_counts_decided_requests():
    workspace = WorkspaceFactory()
    now = timezone.now()
    decided = ApprovalRequestFactory(workspace=workspace)
    decided.decided_at = now + timedelta(hours=2)
    decided.save(update_fields=["decided_at"])
    ApprovalRequestFactory(workspace=workspace)  # never decided

    average = selectors.average_approval_duration_seconds(workspace_id=workspace.id)

    assert average == pytest.approx(2 * 3600, rel=0.01)


@pytest.mark.django_db
def test_average_approval_duration_is_none_with_no_decided_requests():
    workspace = WorkspaceFactory()
    ApprovalRequestFactory(workspace=workspace)

    average = selectors.average_approval_duration_seconds(workspace_id=workspace.id)

    assert average is None
