"""Workspace-scoped read queries.

Every view/serializer that needs workspace-scoped data goes through these
functions rather than building its own queryset — this is the single
place that defines what "belongs to this workspace" / "this user is a
member" means, so a view can't accidentally bypass workspace isolation by
querying the model directly.
"""

from apps.accounts.models import User
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceSettings


def get_membership(user: User, workspace_id) -> WorkspaceMembership | None:
    """The authoritative "is this user a member of this workspace, and
    with what role" check. Never trust a client-supplied role/workspace
    claim — always re-derive it from this query."""
    return (
        WorkspaceMembership.objects.filter(user=user, workspace_id=workspace_id)
        .select_related("workspace")
        .first()
    )


def get_user_workspaces(user: User):
    return Workspace.objects.filter(memberships__user=user).distinct().order_by("name")


def get_workspace_members(workspace_id):
    return (
        WorkspaceMembership.objects.filter(workspace_id=workspace_id)
        .select_related("user")
        .order_by("created_at")
    )


def get_settings(workspace_id) -> WorkspaceSettings | None:
    return WorkspaceSettings.objects.filter(workspace_id=workspace_id).first()
