"""API contract tests for the extraction/review endpoints — workspace
isolation, permissions, optimistic locking, and stable error codes."""

import pytest
from django.urls import reverse

from apps.extraction.models import ExtractionStatus, ValidationSeverity
from apps.workspaces.models import Role
from tests.factories import (
    DocumentExtractionFactory,
    DocumentFactory,
    ExtractedFieldFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMembershipFactory,
)


@pytest.fixture
def workspace():
    return WorkspaceFactory()


def _client_with_role(api_client, workspace, role):
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace, role=role)
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.mark.django_db
class TestDocumentExtractionDetailView:
    def test_returns_the_extraction_with_fields_and_issues(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        extraction = DocumentExtractionFactory(document=document, workspace=workspace)
        ExtractedFieldFactory(extraction=extraction, key="total")
        _client_with_role(api_client, workspace, Role.VIEWER)

        response = api_client.get(
            reverse("document-extraction-detail", args=[workspace.id, document.id])
        )

        assert response.status_code == 200
        assert response.data["status"] == "pending_review"
        assert len(response.data["fields_data"]) == 1

    def test_missing_extraction_returns_404(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        _client_with_role(api_client, workspace, Role.VIEWER)

        response = api_client.get(
            reverse("document-extraction-detail", args=[workspace.id, document.id])
        )

        assert response.status_code == 404

    def test_another_workspaces_extraction_is_not_visible(self, api_client, workspace):
        other_workspace = WorkspaceFactory()
        other_document = DocumentFactory(workspace=other_workspace)
        DocumentExtractionFactory(document=other_document, workspace=other_workspace)
        _client_with_role(api_client, workspace, Role.VIEWER)

        response = api_client.get(
            reverse("document-extraction-detail", args=[workspace.id, other_document.id])
        )

        assert response.status_code == 404

    def test_anonymous_is_rejected(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        DocumentExtractionFactory(document=document, workspace=workspace)

        response = api_client.get(
            reverse("document-extraction-detail", args=[workspace.id, document.id])
        )

        assert response.status_code == 401


@pytest.mark.django_db
class TestExtractedFieldCorrectionView:
    def test_reviewer_can_correct_a_field(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        extraction = DocumentExtractionFactory(document=document, workspace=workspace)
        field = ExtractedFieldFactory(extraction=extraction, key="total", display_value="1.00")
        _client_with_role(api_client, workspace, Role.REVIEWER)

        response = api_client.patch(
            reverse(
                "document-extraction-field-correct", args=[workspace.id, document.id, field.id]
            ),
            {"value": "250.00", "reason": "misread", "expected_version": 1},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["display_value"] == "250.00"
        assert len(response.data["corrections"]) == 1

    def test_viewer_cannot_correct_a_field(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        extraction = DocumentExtractionFactory(document=document, workspace=workspace)
        field = ExtractedFieldFactory(extraction=extraction)
        _client_with_role(api_client, workspace, Role.VIEWER)

        response = api_client.patch(
            reverse(
                "document-extraction-field-correct", args=[workspace.id, document.id, field.id]
            ),
            {"value": "1", "expected_version": 1},
            format="json",
        )

        assert response.status_code == 403

    def test_stale_version_returns_409_with_a_stable_code(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        extraction = DocumentExtractionFactory(document=document, workspace=workspace)
        field = ExtractedFieldFactory(extraction=extraction)
        _client_with_role(api_client, workspace, Role.REVIEWER)

        response = api_client.patch(
            reverse(
                "document-extraction-field-correct", args=[workspace.id, document.id, field.id]
            ),
            {"value": "1", "expected_version": 99},
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "stale_version"

    def test_correcting_an_approved_extraction_is_rejected(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        extraction = DocumentExtractionFactory(
            document=document, workspace=workspace, status=ExtractionStatus.APPROVED
        )
        field = ExtractedFieldFactory(extraction=extraction)
        _client_with_role(api_client, workspace, Role.REVIEWER)

        response = api_client.patch(
            reverse(
                "document-extraction-field-correct", args=[workspace.id, document.id, field.id]
            ),
            {"value": "1", "expected_version": 1},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "extraction_locked"


@pytest.mark.django_db
class TestDocumentExtractionTransitionView:
    def test_finance_manager_can_approve(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        DocumentExtractionFactory(document=document, workspace=workspace)
        _client_with_role(api_client, workspace, Role.FINANCE_MANAGER)

        response = api_client.post(
            reverse("document-extraction-transition", args=[workspace.id, document.id]),
            {"status": "approved", "expected_version": 1},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == "approved"

    def test_reviewer_cannot_approve(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        DocumentExtractionFactory(document=document, workspace=workspace)
        _client_with_role(api_client, workspace, Role.REVIEWER)

        response = api_client.post(
            reverse("document-extraction-transition", args=[workspace.id, document.id]),
            {"status": "approved", "expected_version": 1},
            format="json",
        )

        assert response.status_code == 403

    def test_reviewer_can_reject(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        DocumentExtractionFactory(document=document, workspace=workspace)
        _client_with_role(api_client, workspace, Role.REVIEWER)

        response = api_client.post(
            reverse("document-extraction-transition", args=[workspace.id, document.id]),
            {"status": "rejected", "expected_version": 1},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == "rejected"

    def test_invalid_transition_returns_a_stable_error_code(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        DocumentExtractionFactory(
            document=document, workspace=workspace, status=ExtractionStatus.APPROVED
        )
        _client_with_role(api_client, workspace, Role.FINANCE_MANAGER)

        response = api_client.post(
            reverse("document-extraction-transition", args=[workspace.id, document.id]),
            {"status": "rejected", "expected_version": 1},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "invalid_transition"

    def test_approval_blocked_by_error_severity_issues(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        extraction = DocumentExtractionFactory(document=document, workspace=workspace)
        field = ExtractedFieldFactory(extraction=extraction)
        from apps.extraction.models import ValidationIssue

        ValidationIssue.objects.create(
            extraction=extraction,
            field=field,
            code="required_field_missing",
            message="x",
            severity=ValidationSeverity.ERROR,
        )
        _client_with_role(api_client, workspace, Role.FINANCE_MANAGER)

        response = api_client.post(
            reverse("document-extraction-transition", args=[workspace.id, document.id]),
            {"status": "approved", "expected_version": 1},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "invalid_transition"
