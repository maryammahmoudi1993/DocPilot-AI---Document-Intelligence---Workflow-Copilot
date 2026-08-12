import pytest
from django.urls import reverse

from apps.audit.services import record_event
from apps.workspaces.models import Role
from tests.factories import UserFactory, WorkspaceFactory, WorkspaceMembershipFactory


@pytest.fixture
def workspace():
    return WorkspaceFactory()


def _client_with_role(api_client, workspace, role=Role.VIEWER):
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace, role=role)
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.mark.django_db
class TestAuditEventListView:
    def test_lists_only_this_workspaces_events(self, api_client, workspace):
        other = WorkspaceFactory()
        record_event(event_type="document.uploaded", workspace=workspace)
        record_event(event_type="document.uploaded", workspace=other)
        _client_with_role(api_client, workspace)

        response = api_client.get(reverse("audit-event-list", args=[workspace.id]))

        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_filters_by_event_type(self, api_client, workspace):
        record_event(event_type="approval.requested", workspace=workspace)
        record_event(event_type="approval.approved", workspace=workspace)
        _client_with_role(api_client, workspace)

        response = api_client.get(
            reverse("audit-event-list", args=[workspace.id]), {"event_type": "approval.approved"}
        )

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["event_type"] == "approval.approved"

    def test_anonymous_is_rejected(self, api_client, workspace):
        response = api_client.get(reverse("audit-event-list", args=[workspace.id]))

        assert response.status_code == 401

    def test_no_mutation_endpoints_exist_for_audit_events(self, api_client, workspace):
        """The public API is deliberately read-only end to end — see
        apps/audit/selectors.py's docstring. POST/PUT/PATCH/DELETE on the
        list endpoint must all be rejected as method-not-allowed."""
        _client_with_role(api_client, workspace, Role.ADMIN)
        url = reverse("audit-event-list", args=[workspace.id])

        assert api_client.post(url, {}, format="json").status_code == 405
        assert api_client.put(url, {}, format="json").status_code == 405
        assert api_client.patch(url, {}, format="json").status_code == 405
        assert api_client.delete(url).status_code == 405
