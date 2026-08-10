"""Service-layer tests for apps/processing/services.py — the entry
points documents.services (on upload) and the retry API view call into.
Uses pytest-django's `django_capture_on_commit_callbacks` so the
`transaction.on_commit(...)`-deferred task enqueue is actually observed
without needing a real broker (see apps.processing.services.enqueue_processing).
`unittest.mock` (not pytest-mock, not in this project's dependencies)
patches `run_processing_pipeline.delay` so no test ever actually runs
the pipeline here — this file tests scheduling/idempotency decisions
only, not pipeline behavior (see test_tasks.py for that).
"""

from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from apps.audit.models import AuditEvent
from apps.processing import services
from apps.processing.models import ProcessingJob, ProcessingStage
from tests.factories import DocumentFactory, ProcessingJobFactory, UserFactory


@pytest.mark.django_db
class TestEnqueueProcessing:
    def test_creates_a_job_and_schedules_the_pipeline_task(self, django_capture_on_commit_callbacks):
        document = DocumentFactory()

        with patch("apps.processing.services.run_processing_pipeline.delay") as delay:
            with django_capture_on_commit_callbacks(execute=True):
                job = services.enqueue_processing(document=document)

        assert ProcessingJob.objects.filter(document=document).count() == 1
        assert job.stage == ProcessingStage.QUEUED
        delay.assert_called_once_with(str(job.id))

    def test_a_duplicate_request_while_a_job_is_still_active_returns_the_same_job(
        self, django_capture_on_commit_callbacks
    ):
        document = DocumentFactory()

        with patch("apps.processing.services.run_processing_pipeline.delay") as delay:
            with django_capture_on_commit_callbacks(execute=True):
                first = services.enqueue_processing(document=document)
            with django_capture_on_commit_callbacks(execute=True):
                second = services.enqueue_processing(document=document)

        assert first.id == second.id
        assert ProcessingJob.objects.filter(document=document).count() == 1
        delay.assert_called_once()  # never scheduled twice

    def test_a_new_request_after_the_previous_job_finished_creates_a_fresh_job(
        self, django_capture_on_commit_callbacks
    ):
        document = DocumentFactory()
        ProcessingJobFactory(document=document, workspace=document.workspace, stage=ProcessingStage.COMPLETED)

        with patch("apps.processing.services.run_processing_pipeline.delay"):
            with django_capture_on_commit_callbacks(execute=True):
                job = services.enqueue_processing(document=document)

        assert ProcessingJob.objects.filter(document=document).count() == 2
        assert job.stage == ProcessingStage.QUEUED


@pytest.mark.django_db
class TestRetryProcessing:
    def test_retrying_without_any_failed_job_is_rejected(self):
        document = DocumentFactory()
        actor = UserFactory()

        with pytest.raises(ValidationError):
            services.retry_processing(document=document, actor=actor)

    def test_retrying_a_non_retryable_failure_is_rejected(self):
        document = DocumentFactory()
        actor = UserFactory()
        ProcessingJobFactory(
            document=document,
            workspace=document.workspace,
            stage=ProcessingStage.FAILED,
            is_retryable=False,
            error_code="corrupt_file",
        )

        with pytest.raises(ValidationError):
            services.retry_processing(document=document, actor=actor)

    def test_retrying_a_retryable_failure_creates_a_new_job_and_audit_event(
        self, django_capture_on_commit_callbacks
    ):
        document = DocumentFactory()
        actor = UserFactory()
        ProcessingJobFactory(
            document=document,
            workspace=document.workspace,
            stage=ProcessingStage.FAILED,
            is_retryable=True,
            error_code="ocr_provider_timeout",
        )

        with patch("apps.processing.services.run_processing_pipeline.delay") as delay:
            with django_capture_on_commit_callbacks(execute=True):
                job = services.retry_processing(document=document, actor=actor)

        assert job.stage == ProcessingStage.QUEUED
        assert ProcessingJob.objects.filter(document=document).count() == 2
        delay.assert_called_once_with(str(job.id))
        assert AuditEvent.objects.filter(
            event_type="document.processing_retried", workspace=document.workspace
        ).exists()


@pytest.mark.django_db
def test_get_latest_processing_job_returns_the_most_recent_one():
    document = DocumentFactory()
    ProcessingJobFactory(document=document, workspace=document.workspace, stage=ProcessingStage.FAILED)
    latest = ProcessingJobFactory(document=document, workspace=document.workspace, stage=ProcessingStage.COMPLETED)

    result = services.get_latest_processing_job(document=document)

    assert result.id == latest.id
