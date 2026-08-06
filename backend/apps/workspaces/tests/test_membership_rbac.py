import pytest
from django.urls import reverse

from apps.workspaces.models import Role, WorkspaceMembership
from tests.factories import UserFactory, WorkspaceFactory, WorkspaceMembershipFactory


@pytest.mark.django_db
def test_owner_can_add_a_member(api_client):
    workspace = WorkspaceFactory()
    owner = UserFactory()
    WorkspaceMembershipFactory(user=owner, workspace=workspace, role=Role.OWNER)
    new_user = UserFactory()
    api_client.force_authenticate(user=owner)

    response = api_client.post(
        reverse("workspace-members", args=[workspace.id]),
        {"email": new_user.email, "role": Role.REVIEWER},
    )

    assert response.status_code == 201
    assert WorkspaceMembership.objects.filter(
        workspace=workspace, user=new_user, role=Role.REVIEWER
    ).exists()


@pytest.mark.django_db
def test_admin_can_add_a_member(api_client):
    workspace = WorkspaceFactory()
    admin = UserFactory()
    WorkspaceMembershipFactory(user=admin, workspace=workspace, role=Role.ADMIN)
    new_user = UserFactory()
    api_client.force_authenticate(user=admin)

    response = api_client.post(
        reverse("workspace-members", args=[workspace.id]),
        {"email": new_user.email, "role": Role.VIEWER},
    )

    assert response.status_code == 201


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.FINANCE_MANAGER, Role.REVIEWER, Role.VIEWER])
def test_non_manager_roles_cannot_add_members(api_client, role):
    """Finance Manager, Reviewer, and Viewer all get exactly the same
    (denied) outcome for membership management — none of them are
    management roles, regardless of their other future permissions."""
    workspace = WorkspaceFactory()
    member = UserFactory()
    WorkspaceMembershipFactory(user=member, workspace=workspace, role=role)
    new_user = UserFactory()
    api_client.force_authenticate(user=member)

    response = api_client.post(
        reverse("workspace-members", args=[workspace.id]),
        {"email": new_user.email, "role": Role.VIEWER},
    )

    assert response.status_code == 403
    assert response.data["error"]["code"] == "permission_denied"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.FINANCE_MANAGER, Role.REVIEWER, Role.VIEWER])
def test_every_member_can_still_read_the_member_list(api_client, role):
    """Read access is for every member; only *managing* membership is
    restricted to Owner/Admin."""
    workspace = WorkspaceFactory()
    member = UserFactory()
    WorkspaceMembershipFactory(user=member, workspace=workspace, role=role)
    api_client.force_authenticate(user=member)

    response = api_client.get(reverse("workspace-members", args=[workspace.id]))

    assert response.status_code == 200


@pytest.mark.django_db
def test_owner_cannot_be_removed_directly(api_client):
    workspace = WorkspaceFactory()
    owner = UserFactory()
    owner_membership = WorkspaceMembershipFactory(user=owner, workspace=workspace, role=Role.OWNER)
    admin = UserFactory()
    WorkspaceMembershipFactory(user=admin, workspace=workspace, role=Role.ADMIN)
    api_client.force_authenticate(user=admin)

    response = api_client.delete(
        reverse("workspace-member-detail", args=[workspace.id, owner_membership.id])
    )

    assert response.status_code == 403
    assert WorkspaceMembership.objects.filter(id=owner_membership.id, role=Role.OWNER).exists()


@pytest.mark.django_db
def test_admin_can_remove_a_reviewer(api_client):
    workspace = WorkspaceFactory()
    admin = UserFactory()
    WorkspaceMembershipFactory(user=admin, workspace=workspace, role=Role.ADMIN)
    target = WorkspaceMembershipFactory(workspace=workspace, role=Role.REVIEWER)
    api_client.force_authenticate(user=admin)

    response = api_client.delete(reverse("workspace-member-detail", args=[workspace.id, target.id]))

    assert response.status_code == 204
    assert not WorkspaceMembership.objects.filter(id=target.id).exists()


@pytest.mark.django_db
def test_owner_can_change_a_members_role(api_client):
    workspace = WorkspaceFactory()
    owner = UserFactory()
    WorkspaceMembershipFactory(user=owner, workspace=workspace, role=Role.OWNER)
    target = WorkspaceMembershipFactory(workspace=workspace, role=Role.VIEWER)
    api_client.force_authenticate(user=owner)

    response = api_client.patch(
        reverse("workspace-member-detail", args=[workspace.id, target.id]), {"role": Role.REVIEWER}
    )

    assert response.status_code == 200
    target.refresh_from_db()
    assert target.role == Role.REVIEWER


@pytest.mark.django_db
def test_cannot_change_role_to_owner_directly(api_client):
    workspace = WorkspaceFactory()
    owner = UserFactory()
    WorkspaceMembershipFactory(user=owner, workspace=workspace, role=Role.OWNER)
    target = WorkspaceMembershipFactory(workspace=workspace, role=Role.VIEWER)
    api_client.force_authenticate(user=owner)

    response = api_client.patch(
        reverse("workspace-member-detail", args=[workspace.id, target.id]), {"role": Role.OWNER}
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_owner_can_transfer_ownership(api_client):
    workspace = WorkspaceFactory()
    owner = UserFactory()
    owner_membership = WorkspaceMembershipFactory(user=owner, workspace=workspace, role=Role.OWNER)
    successor = WorkspaceMembershipFactory(workspace=workspace, role=Role.ADMIN)
    api_client.force_authenticate(user=owner)

    response = api_client.post(
        reverse("workspace-transfer-ownership", args=[workspace.id]),
        {"new_owner_membership_id": str(successor.id)},
    )

    assert response.status_code == 204
    owner_membership.refresh_from_db()
    successor.refresh_from_db()
    assert owner_membership.role == Role.ADMIN
    assert successor.role == Role.OWNER


@pytest.mark.django_db
def test_non_owner_cannot_transfer_ownership(api_client):
    workspace = WorkspaceFactory()
    admin = UserFactory()
    WorkspaceMembershipFactory(user=admin, workspace=workspace, role=Role.ADMIN)
    other = WorkspaceMembershipFactory(workspace=workspace, role=Role.VIEWER)
    api_client.force_authenticate(user=admin)

    response = api_client.post(
        reverse("workspace-transfer-ownership", args=[workspace.id]),
        {"new_owner_membership_id": str(other.id)},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_membership_changes_create_audit_events(api_client):
    from apps.audit.models import AuditEvent

    workspace = WorkspaceFactory()
    owner = UserFactory()
    WorkspaceMembershipFactory(user=owner, workspace=workspace, role=Role.OWNER)
    new_user = UserFactory()
    api_client.force_authenticate(user=owner)

    api_client.post(
        reverse("workspace-members", args=[workspace.id]),
        {"email": new_user.email, "role": Role.VIEWER},
    )

    assert AuditEvent.objects.filter(
        event_type="workspace.member_added", workspace=workspace
    ).exists()
