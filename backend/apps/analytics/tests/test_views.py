import pytest
from django.urls import reverse

from apps.processing.models import ProcessingStage
from apps.workspaces.models import Role
from tests.factories import (
    ProcessingJobFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMembershipFactory,
)


@pytest.fixture
def workspace():
    return WorkspaceFactory()


def _client_with_role(api_client, workspace, role=Role.VIEWER):
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace, role=role)
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.mark.django_db
class TestDashboardSummaryView:
    def test_returns_workspace_scoped_counts(self, api_client, workspace):
        ProcessingJobFactory(
            document__workspace=workspace, workspace=workspace, stage=ProcessingStage.QUEUED
        )
        _client_with_role(api_client, workspace)

        response = api_client.get(reverse("dashboard-summary", args=[workspace.id]))

        assert response.status_code == 200
        assert response.data["total_documents"] == 1

    def test_anonymous_is_rejected(self, api_client, workspace):
        response = api_client.get(reverse("dashboard-summary", args=[workspace.id]))

        assert response.status_code == 401

    def test_a_non_member_cannot_read_another_workspaces_dashboard(self, api_client, workspace):
        other = WorkspaceFactory()
        _client_with_role(api_client, workspace)

        response = api_client.get(reverse("dashboard-summary", args=[other.id]))

        assert response.status_code == 403


@pytest.mark.django_db
class TestAnalyticsOverviewView:
    def test_defaults_to_a_trailing_thirty_day_range(self, api_client, workspace):
        _client_with_role(api_client, workspace)

        response = api_client.get(reverse("analytics-overview", args=[workspace.id]))

        assert response.status_code == 200
        assert len(response.data["processing_trends"]) == 30
        assert response.data["extraction_accuracy"]["is_illustrative"] is True

    def test_accepts_an_explicit_date_range(self, api_client, workspace):
        _client_with_role(api_client, workspace)

        response = api_client.get(
            reverse("analytics-overview", args=[workspace.id]),
            {"since": "2026-08-01", "until": "2026-08-03"},
        )

        assert response.status_code == 200
        assert len(response.data["processing_trends"]) == 3

    def test_rejects_since_after_until(self, api_client, workspace):
        _client_with_role(api_client, workspace)

        response = api_client.get(
            reverse("analytics-overview", args=[workspace.id]),
            {"since": "2026-08-10", "until": "2026-08-01"},
        )

        assert response.status_code == 400
