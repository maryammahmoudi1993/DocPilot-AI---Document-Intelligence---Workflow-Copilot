import pytest

from apps.workspaces.models import Role
from apps.workspaces.selectors import get_membership, get_user_workspaces, get_workspace_members
from tests.factories import UserFactory, WorkspaceFactory, WorkspaceMembershipFactory


@pytest.mark.django_db
def test_get_workspace_members_never_returns_another_workspaces_members():
    workspace_a = WorkspaceFactory()
    workspace_b = WorkspaceFactory()
    WorkspaceMembershipFactory(workspace=workspace_a, role=Role.VIEWER)
    WorkspaceMembershipFactory(workspace=workspace_b, role=Role.VIEWER)

    members = get_workspace_members(workspace_a.id)

    assert all(m.workspace_id == workspace_a.id for m in members)
    assert members.count() == 1


@pytest.mark.django_db
def test_get_membership_returns_none_for_a_non_member():
    user = UserFactory()
    workspace = WorkspaceFactory()

    assert get_membership(user, workspace.id) is None


@pytest.mark.django_db
def test_get_user_workspaces_only_returns_workspaces_with_real_membership():
    user = UserFactory()
    member_workspace = WorkspaceFactory()
    WorkspaceMembershipFactory(user=user, workspace=member_workspace, role=Role.VIEWER)
    WorkspaceFactory()  # a workspace the user has nothing to do with

    workspaces = list(get_user_workspaces(user))

    assert workspaces == [member_workspace]
