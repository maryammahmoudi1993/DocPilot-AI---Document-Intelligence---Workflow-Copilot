"""Workspace membership business logic.

Kept out of views/serializers (non-negotiable project rule) so it can be
unit-tested directly and so every membership mutation goes through the
same transactional, audit-logged path regardless of which view calls it.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.workspaces.models import ASSIGNABLE_ROLES, Role, Workspace, WorkspaceMembership


def add_member(
    *, workspace: Workspace, actor_membership: WorkspaceMembership, email: str, role: str
) -> WorkspaceMembership:
    if role not in ASSIGNABLE_ROLES:
        raise ValidationError({"role": "Cannot assign this role directly."})

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        # Portfolio scope: no invite-by-email/signup flow yet — the user
        # must already have an account.
        raise ValidationError({"email": "No user with that email exists."})

    with transaction.atomic():
        if WorkspaceMembership.objects.filter(workspace=workspace, user=user).exists():
            raise ValidationError({"email": "This user is already a member of the workspace."})
        membership = WorkspaceMembership.objects.create(workspace=workspace, user=user, role=role)
        record_event(
            event_type="workspace.member_added",
            actor=actor_membership.user,
            workspace=workspace,
            metadata={"member_user_id": user.id, "role": role},
        )
    return membership


def change_role(
    *, membership: WorkspaceMembership, actor_membership: WorkspaceMembership, new_role: str
) -> WorkspaceMembership:
    if membership.role == Role.OWNER:
        raise PermissionDenied("Use the transfer-ownership action to change the owner.")
    if new_role not in ASSIGNABLE_ROLES:
        raise ValidationError({"role": "Cannot assign this role directly."})

    with transaction.atomic():
        old_role = membership.role
        membership.role = new_role
        membership.save(update_fields=["role"])
        record_event(
            event_type="workspace.member_role_changed",
            actor=actor_membership.user,
            workspace=membership.workspace,
            metadata={
                "member_user_id": membership.user_id,
                "old_role": old_role,
                "new_role": new_role,
            },
        )
    return membership


def remove_member(
    *, membership: WorkspaceMembership, actor_membership: WorkspaceMembership
) -> None:
    if membership.role == Role.OWNER:
        raise PermissionDenied("The workspace owner cannot be removed. Transfer ownership first.")

    with transaction.atomic():
        record_event(
            event_type="workspace.member_removed",
            actor=actor_membership.user,
            workspace=membership.workspace,
            metadata={"member_user_id": membership.user_id, "role": membership.role},
        )
        membership.delete()


def transfer_ownership(
    *,
    workspace: Workspace,
    current_owner_membership: WorkspaceMembership,
    new_owner_membership: WorkspaceMembership,
) -> None:
    if current_owner_membership.role != Role.OWNER:
        raise PermissionDenied("Only the current owner can transfer ownership.")
    if new_owner_membership.workspace_id != workspace.id:
        raise ValidationError(
            {"new_owner_membership_id": "Membership does not belong to this workspace."}
        )
    if new_owner_membership.id == current_owner_membership.id:
        raise ValidationError({"new_owner_membership_id": "That membership is already the owner."})

    with transaction.atomic():
        current_owner_membership.role = Role.ADMIN
        current_owner_membership.save(update_fields=["role"])
        new_owner_membership.role = Role.OWNER
        new_owner_membership.save(update_fields=["role"])
        record_event(
            event_type="workspace.ownership_transferred",
            actor=current_owner_membership.user,
            workspace=workspace,
            metadata={
                "previous_owner_user_id": current_owner_membership.user_id,
                "new_owner_user_id": new_owner_membership.user_id,
            },
        )


def set_active_workspace(*, user: User, workspace_id) -> Workspace:
    """UX convenience only — see the module docstring in permissions.py
    for why this is never used to authorize anything."""
    membership = (
        WorkspaceMembership.objects.filter(user=user, workspace_id=workspace_id)
        .select_related("workspace")
        .first()
    )
    if membership is None:
        raise PermissionDenied("You are not a member of that workspace.")

    with transaction.atomic():
        user.active_workspace = membership.workspace
        user.save(update_fields=["active_workspace"])
        record_event(
            event_type="auth.active_workspace_changed",
            actor=user,
            workspace=membership.workspace,
            metadata={},
        )
    return membership.workspace
