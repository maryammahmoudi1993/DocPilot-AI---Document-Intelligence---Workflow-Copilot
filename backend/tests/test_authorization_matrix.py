"""A consolidated cross-cutting authorization check: for a representative
spread of workspace-scoped endpoints, (1) an authenticated user who is
NOT a member of the target workspace is denied, and (2) an anonymous
caller is denied. Individual apps already carry their own deeper
authorization tests (decision permissions, role gating, etc.) — this
file exists purely to guard the *workspace-membership boundary* in one
place across the whole API surface, so a future endpoint that forgets
to wire IsWorkspaceMember shows up here instead of only in its own
app's test suite (or not at all).
"""

import pytest
from django.urls import reverse

from apps.workspaces.models import Role
from tests.factories import UserFactory, WorkspaceFactory, WorkspaceMembershipFactory

# (url_name, args_from_workspace_id, namespace) — every entry is a GET
# (list) endpoint that exists purely behind workspace membership, no
# extra path params beyond workspace_id.
WORKSPACE_SCOPED_LIST_ENDPOINTS = [
    "document-list",
    "workflow-list",
    "approval-list",
    "audit-event-list",
    "dashboard-summary",
    "analytics-overview",
    "workspace-settings",
    "assistant-conversation-list",
    "notifications:notification-list",
    "integrations:webhook-endpoint-list",
]


@pytest.fixture
def two_workspaces():
    return WorkspaceFactory(), WorkspaceFactory()


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", WORKSPACE_SCOPED_LIST_ENDPOINTS)
def test_a_non_member_cannot_reach_another_workspaces_endpoint(
    api_client, two_workspaces, url_name
):
    workspace_a, workspace_b = two_workspaces
    outsider = UserFactory()
    WorkspaceMembershipFactory(user=outsider, workspace=workspace_a, role=Role.ADMIN)
    api_client.force_authenticate(user=outsider)

    response = api_client.get(reverse(url_name, args=[workspace_b.id]))

    assert response.status_code == 403, f"{url_name} did not reject a cross-workspace caller"


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", WORKSPACE_SCOPED_LIST_ENDPOINTS)
def test_an_anonymous_caller_cannot_reach_any_workspace_endpoint(
    api_client, two_workspaces, url_name
):
    workspace_a, _ = two_workspaces

    response = api_client.get(reverse(url_name, args=[workspace_a.id]))

    assert response.status_code == 401, f"{url_name} did not reject an anonymous caller"


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", WORKSPACE_SCOPED_LIST_ENDPOINTS)
def test_a_real_member_can_reach_their_own_workspaces_endpoint(
    api_client, two_workspaces, url_name
):
    workspace_a, _ = two_workspaces
    member = UserFactory()
    WorkspaceMembershipFactory(user=member, workspace=workspace_a, role=Role.ADMIN)
    api_client.force_authenticate(user=member)

    response = api_client.get(reverse(url_name, args=[workspace_a.id]))

    assert response.status_code == 200, f"{url_name} rejected a real member of the workspace"
