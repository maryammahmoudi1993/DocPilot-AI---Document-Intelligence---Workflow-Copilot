"""API tests for the processing status/retry endpoints — workspace
isolation, permissions, and the stable response shape. Pipeline
execution itself is mocked out (`run_processing_pipeline.delay`) since
these are view-contract tests, not pipeline tests (see test_tasks.py).
"""

from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.processing.models import ProcessingStage
from tests.factories import (
    DocumentFactory,
    ProcessingJobFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMembershipFactory,
)


@pytest.fixture
def member_client(api_client):
    workspace = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace)
    api_client.force_authenticate(user=user)
    return api_client, workspace, user


@pytest.mark.django_db
class TestProcessingStatusView:
    def test_returns_the_latest_job_for_the_document(self, member_client):
        api_client, workspace, _ = member_client
        document = DocumentFactory(workspace=workspace)
        ProcessingJobFactory(document=document, workspace=workspace, stage=ProcessingStage.FAILED)
        latest = ProcessingJobFactory(document=document, workspace=workspace, stage=ProcessingStage.RUNNING_OCR)

        response = api_client.get(
            reverse("document-processing-status", args=[workspace.id, document.id])
        )

        assert response.status_code == 200
        assert response.data["id"] == str(latest.id)
        assert response.data["stage"] == "running_ocr"

    def test_a_document_with_no_processing_job_returns_404(self, member_client):
        api_client, workspace, _ = member_client
        document = DocumentFactory(workspace=workspace)

        response = api_client.get(
            reverse("document-processing-status", args=[workspace.id, document.id])
        )

        assert response.status_code == 404

    def test_a_document_from_another_workspace_returns_404(self, member_client):
        api_client, workspace, _ = member_client
        other_workspace = WorkspaceFactory()
        other_document = DocumentFactory(workspace=other_workspace)
        ProcessingJobFactory(document=other_document, workspace=other_workspace)

        response = api_client.get(
            reverse("document-processing-status", args=[workspace.id, other_document.id])
        )

        assert response.status_code == 404

    def test_anonymous_cannot_view_status(self, api_client):
        workspace = WorkspaceFactory()
        document = DocumentFactory(workspace=workspace)
        ProcessingJobFactory(document=document, workspace=workspace)

        response = api_client.get(
            reverse("document-processing-status", args=[workspace.id, document.id])
        )

        assert response.status_code == 401


@pytest.mark.django_db
class TestProcessingRetryView:
    def test_retrying_a_failed_retryable_job_succeeds(self, member_client):
        api_client, workspace, _ = member_client
        document = DocumentFactory(workspace=workspace)
        ProcessingJobFactory(
            document=document,
            workspace=workspace,
            stage=ProcessingStage.FAILED,
            is_retryable=True,
            error_code="ocr_provider_timeout",
        )

        with patch("apps.processing.services.run_processing_pipeline.delay"):
            response = api_client.post(
                reverse("document-processing-retry", args=[workspace.id, document.id])
            )

        assert response.status_code == 201
        assert response.data["stage"] == "queued"

    def test_retrying_without_a_failed_job_is_rejected(self, member_client):
        api_client, workspace, _ = member_client
        document = DocumentFactory(workspace=workspace)

        response = api_client.post(
            reverse("document-processing-retry", args=[workspace.id, document.id])
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"

    def test_a_document_from_another_workspace_cannot_be_retried(self, member_client):
        api_client, workspace, _ = member_client
        other_workspace = WorkspaceFactory()
        other_document = DocumentFactory(workspace=other_workspace)
        ProcessingJobFactory(
            document=other_document, workspace=other_workspace, stage=ProcessingStage.FAILED, is_retryable=True
        )

        response = api_client.post(
            reverse("document-processing-retry", args=[workspace.id, other_document.id])
        )

        assert response.status_code == 404

    def test_anonymous_cannot_retry(self, api_client):
        workspace = WorkspaceFactory()
        document = DocumentFactory(workspace=workspace)

        response = api_client.post(
            reverse("document-processing-retry", args=[workspace.id, document.id])
        )

        assert response.status_code == 401
