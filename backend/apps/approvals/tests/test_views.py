import pytest
from django.urls import reverse

from apps.approvals.models import ApprovalStatus
from apps.workspaces.models import Role
from tests.factories import (
    ApprovalRequestFactory,
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
class TestApprovalListView:
    def test_lists_only_this_workspaces_approvals(self, api_client, workspace):
        ApprovalRequestFactory(workspace=workspace)
        ApprovalRequestFactory()  # another workspace
        _client_with_role(api_client, workspace)

        response = api_client.get(reverse("approval-list", args=[workspace.id]))

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_filters_by_status(self, api_client, workspace):
        ApprovalRequestFactory(workspace=workspace, status=ApprovalStatus.PENDING)
        ApprovalRequestFactory(workspace=workspace, status=ApprovalStatus.APPROVED)
        _client_with_role(api_client, workspace)

        response = api_client.get(
            reverse("approval-list", args=[workspace.id]), {"status": "approved"}
        )

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["status"] == "approved"

    def test_anonymous_is_rejected(self, api_client, workspace):
        response = api_client.get(reverse("approval-list", args=[workspace.id]))

        assert response.status_code == 401


@pytest.mark.django_db
class TestApprovalDetailView:
    def test_returns_404_for_another_workspaces_approval(self, api_client, workspace):
        other = ApprovalRequestFactory()
        _client_with_role(api_client, workspace)

        response = api_client.get(reverse("approval-detail", args=[workspace.id, other.id]))

        assert response.status_code == 404


@pytest.mark.django_db
class TestApprovalDecisionView:
    def test_owner_or_admin_can_always_decide(self, api_client, workspace):
        approval = ApprovalRequestFactory(workspace=workspace, assigned_role="reviewer")
        _client_with_role(api_client, workspace, Role.ADMIN)

        response = api_client.post(
            reverse("approval-decide", args=[workspace.id, approval.id]),
            {"status": "approved"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == "approved"

    def test_a_member_whose_role_does_not_match_is_forbidden(self, api_client, workspace):
        approval = ApprovalRequestFactory(workspace=workspace, assigned_role=Role.REVIEWER)
        _client_with_role(api_client, workspace, Role.FINANCE_MANAGER)

        response = api_client.post(
            reverse("approval-decide", args=[workspace.id, approval.id]),
            {"status": "approved"},
            format="json",
        )

        assert response.status_code == 403

    def test_a_member_whose_role_matches_the_assigned_role_can_decide(self, api_client, workspace):
        approval = ApprovalRequestFactory(workspace=workspace, assigned_role=Role.REVIEWER)
        _client_with_role(api_client, workspace, Role.REVIEWER)

        response = api_client.post(
            reverse("approval-decide", args=[workspace.id, approval.id]),
            {"status": "rejected", "reason": "not needed"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == "rejected"

    def test_invalid_transition_returns_a_stable_error_code(self, api_client, workspace):
        approval = ApprovalRequestFactory(workspace=workspace, status=ApprovalStatus.APPROVED)
        _client_with_role(api_client, workspace, Role.ADMIN)

        response = api_client.post(
            reverse("approval-decide", args=[workspace.id, approval.id]),
            {"status": "rejected"},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "invalid_approval_transition"

    def test_repeated_identical_decision_is_idempotent(self, api_client, workspace):
        approval = ApprovalRequestFactory(workspace=workspace)
        _client_with_role(api_client, workspace, Role.ADMIN)
        url = reverse("approval-decide", args=[workspace.id, approval.id])
        api_client.post(url, {"status": "approved"}, format="json")

        response = api_client.post(url, {"status": "approved"}, format="json")

        assert response.status_code == 200
        assert response.data["status"] == "approved"

    def test_approval_from_another_workspace_is_not_found(self, api_client, workspace):
        other = ApprovalRequestFactory()
        _client_with_role(api_client, workspace, Role.ADMIN)

        response = api_client.post(
            reverse("approval-decide", args=[workspace.id, other.id]),
            {"status": "approved"},
            format="json",
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestApprovalCommentListCreateView:
    def test_a_workspace_member_can_comment(self, api_client, workspace):
        approval = ApprovalRequestFactory(workspace=workspace)
        _client_with_role(api_client, workspace, Role.REVIEWER)

        response = api_client.post(
            reverse("approval-comments", args=[workspace.id, approval.id]),
            {"body": "Needs another look."},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["body"] == "Needs another look."
