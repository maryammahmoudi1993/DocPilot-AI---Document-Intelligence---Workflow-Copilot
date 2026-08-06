"""Direct unit tests for the service layer's defense-in-depth checks —
rules the API/serializer layer already enforces too (e.g. you can't pick
"owner" as a role at all, per ChoiceField), but the service layer
re-validates independently since it's the actual authority, not the view.
"""

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.workspaces import services
from apps.workspaces.models import Role
from tests.factories import UserFactory, WorkspaceFactory, WorkspaceMembershipFactory


@pytest.mark.django_db
def test_add_member_rejects_owner_role():
    workspace = WorkspaceFactory()
    actor = WorkspaceMembershipFactory(workspace=workspace, role=Role.OWNER)

    with pytest.raises(ValidationError):
        services.add_member(
            workspace=workspace, actor_membership=actor, email="x@example.com", role=Role.OWNER
        )


@pytest.mark.django_db
def test_add_member_rejects_unknown_email():
    workspace = WorkspaceFactory()
    actor = WorkspaceMembershipFactory(workspace=workspace, role=Role.OWNER)

    with pytest.raises(ValidationError):
        services.add_member(
            workspace=workspace,
            actor_membership=actor,
            email="nobody@example.com",
            role=Role.VIEWER,
        )


@pytest.mark.django_db
def test_add_member_rejects_an_existing_member():
    workspace = WorkspaceFactory()
    actor = WorkspaceMembershipFactory(workspace=workspace, role=Role.OWNER)
    existing = WorkspaceMembershipFactory(workspace=workspace, role=Role.VIEWER)

    with pytest.raises(ValidationError):
        services.add_member(
            workspace=workspace,
            actor_membership=actor,
            email=existing.user.email,
            role=Role.REVIEWER,
        )


@pytest.mark.django_db
def test_change_role_refuses_to_touch_the_owner_membership():
    workspace = WorkspaceFactory()
    owner_membership = WorkspaceMembershipFactory(workspace=workspace, role=Role.OWNER)
    actor = WorkspaceMembershipFactory(workspace=workspace, role=Role.ADMIN)

    with pytest.raises(PermissionDenied):
        services.change_role(
            membership=owner_membership, actor_membership=actor, new_role=Role.ADMIN
        )


@pytest.mark.django_db
def test_change_role_rejects_owner_as_the_new_role():
    workspace = WorkspaceFactory()
    target = WorkspaceMembershipFactory(workspace=workspace, role=Role.VIEWER)
    actor = WorkspaceMembershipFactory(workspace=workspace, role=Role.OWNER)

    with pytest.raises(ValidationError):
        services.change_role(membership=target, actor_membership=actor, new_role=Role.OWNER)


@pytest.mark.django_db
def test_transfer_ownership_requires_the_actor_to_actually_be_owner():
    workspace = WorkspaceFactory()
    not_owner = WorkspaceMembershipFactory(workspace=workspace, role=Role.ADMIN)
    successor = WorkspaceMembershipFactory(workspace=workspace, role=Role.VIEWER)

    with pytest.raises(PermissionDenied):
        services.transfer_ownership(
            workspace=workspace, current_owner_membership=not_owner, new_owner_membership=successor
        )


@pytest.mark.django_db
def test_transfer_ownership_rejects_a_membership_from_another_workspace():
    workspace = WorkspaceFactory()
    other_workspace = WorkspaceFactory()
    owner = WorkspaceMembershipFactory(workspace=workspace, role=Role.OWNER)
    foreign_membership = WorkspaceMembershipFactory(workspace=other_workspace, role=Role.ADMIN)

    with pytest.raises(ValidationError):
        services.transfer_ownership(
            workspace=workspace,
            current_owner_membership=owner,
            new_owner_membership=foreign_membership,
        )


@pytest.mark.django_db
def test_transfer_ownership_rejects_transferring_to_self():
    workspace = WorkspaceFactory()
    owner = WorkspaceMembershipFactory(workspace=workspace, role=Role.OWNER)

    with pytest.raises(ValidationError):
        services.transfer_ownership(
            workspace=workspace, current_owner_membership=owner, new_owner_membership=owner
        )


@pytest.mark.django_db
def test_set_active_workspace_rejects_a_non_member():
    user = UserFactory()
    workspace = WorkspaceFactory()

    with pytest.raises(PermissionDenied):
        services.set_active_workspace(user=user, workspace_id=workspace.id)
