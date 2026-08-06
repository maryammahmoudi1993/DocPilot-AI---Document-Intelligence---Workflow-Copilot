import pytest
from django.urls import reverse

from apps.workspaces.models import Role
from tests.factories import UserFactory, WorkspaceFactory, WorkspaceMembershipFactory


@pytest.mark.django_db
def test_anonymous_cannot_list_workspace_members(api_client):
    workspace = WorkspaceFactory()

    response = api_client.get(reverse("workspace-members", args=[workspace.id]))

    assert response.status_code == 401


@pytest.mark.django_db
def test_user_cannot_read_a_workspace_they_are_not_a_member_of(api_client):
    workspace_a = WorkspaceFactory()
    workspace_b = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace_a, role=Role.ADMIN)
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("workspace-members", args=[workspace_b.id]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_user_cannot_mutate_a_workspace_they_are_not_a_member_of(api_client):
    workspace_a = WorkspaceFactory()
    workspace_b = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace_a, role=Role.OWNER)
    other_user = UserFactory()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("workspace-members", args=[workspace_b.id]),
        {"email": other_user.email, "role": Role.VIEWER},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_role_does_not_carry_over_to_a_different_workspace(api_client):
    """Being Admin in workspace A must not grant any power in workspace B
    — role is scoped per-workspace, never global."""
    workspace_a = WorkspaceFactory()
    workspace_b = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace_a, role=Role.ADMIN)
    # Not a member of workspace_b at all.
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("workspace-members", args=[workspace_b.id]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_workspace_list_only_returns_the_callers_own_workspaces(api_client):
    workspace_a = WorkspaceFactory()
    workspace_b = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace_a, role=Role.VIEWER)
    WorkspaceMembershipFactory(workspace=workspace_b, role=Role.VIEWER)  # a different user
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("workspace-list"))

    assert response.status_code == 200
    returned_ids = {w["id"] for w in response.data}
    assert returned_ids == {str(workspace_a.id)}


@pytest.mark.django_db
def test_membership_detail_404s_for_a_membership_in_a_different_workspace(api_client):
    """A membership_id that's real, but belongs to another workspace, must
    not be reachable through this workspace's URL (IDOR check)."""
    workspace_a = WorkspaceFactory()
    workspace_b = WorkspaceFactory()
    owner = UserFactory()
    WorkspaceMembershipFactory(user=owner, workspace=workspace_a, role=Role.OWNER)
    foreign_membership = WorkspaceMembershipFactory(workspace=workspace_b, role=Role.VIEWER)
    api_client.force_authenticate(user=owner)

    response = api_client.delete(
        reverse("workspace-member-detail", args=[workspace_a.id, foreign_membership.id])
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_active_workspace_selection_cannot_be_forged(api_client):
    """Setting active_workspace to a workspace the user does not belong to
    must be rejected — and even if it somehow weren't, workspace-scoped
    endpoints never trust that pointer for authorization (see
    test_admin_role_does_not_carry_over_to_a_different_workspace)."""
    user = UserFactory()
    other_workspace = WorkspaceFactory()  # user is NOT a member
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse("auth-active-workspace"), {"workspace_id": str(other_workspace.id)}
    )

    assert response.status_code == 403
    user.refresh_from_db()
    assert user.active_workspace_id != other_workspace.id


@pytest.mark.django_db
def test_active_workspace_selection_succeeds_for_a_real_membership(api_client):
    user = UserFactory()
    workspace = WorkspaceFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace, role=Role.VIEWER)
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse("auth-active-workspace"), {"workspace_id": str(workspace.id)}
    )

    assert response.status_code == 204
    user.refresh_from_db()
    assert user.active_workspace_id == workspace.id
