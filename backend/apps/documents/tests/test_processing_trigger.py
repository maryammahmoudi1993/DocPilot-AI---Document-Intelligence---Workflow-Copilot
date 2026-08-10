"""Verifies a successful upload schedules the async processing pipeline
(Phase 4 Definition of Done: "Upload returns quickly. Processing runs
outside the HTTP request.") without actually running it — pipeline
behavior itself belongs to apps/processing/tests/test_tasks.py.
"""

from unittest.mock import patch

import pytest
from django.urls import reverse

from tests.factories import UserFactory, WorkspaceFactory, WorkspaceMembershipFactory

PDF_BYTES = b"%PDF-1.4\n%mock pdf content for tests\n"


@pytest.fixture
def member_client(api_client):
    workspace = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace)
    api_client.force_authenticate(user=user)
    return api_client, workspace, user


@pytest.mark.django_db
def test_a_successful_upload_schedules_processing(
    member_client, fake_storage, django_capture_on_commit_callbacks
):
    from django.core.files.uploadedfile import SimpleUploadedFile

    api_client, workspace, _ = member_client

    with patch("apps.processing.services.run_processing_pipeline.delay") as delay:
        with django_capture_on_commit_callbacks(execute=True):
            response = api_client.post(
                reverse("document-list", args=[workspace.id]),
                {"file": SimpleUploadedFile("invoice.pdf", PDF_BYTES, content_type="application/pdf")},
                format="multipart",
            )

    assert response.status_code == 201
    delay.assert_called_once()


@pytest.mark.django_db
def test_a_rejected_upload_never_schedules_processing(
    member_client, fake_storage, django_capture_on_commit_callbacks
):
    from django.core.files.uploadedfile import SimpleUploadedFile

    api_client, workspace, _ = member_client

    with patch("apps.processing.services.run_processing_pipeline.delay") as delay:
        with django_capture_on_commit_callbacks(execute=True):
            response = api_client.post(
                reverse("document-list", args=[workspace.id]),
                {"file": SimpleUploadedFile("malware.exe", b"MZ...", content_type="application/octet-stream")},
                format="multipart",
            )

    assert response.status_code == 400
    delay.assert_not_called()
