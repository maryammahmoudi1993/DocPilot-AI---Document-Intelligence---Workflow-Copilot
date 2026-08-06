"""DRF permission classes enforcing workspace isolation and RBAC.

Every permission check re-derives the caller's role from a real
WorkspaceMembership row (via selectors.get_membership) keyed off the
`workspace_id` URL kwarg — never from a client-supplied header, cookie,
or the user's `active_workspace` convenience pointer. That is what makes
"active workspace selection cannot be forged" true: forging the
*preselected* workspace changes nothing about what a request is actually
authorized to touch.
"""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.workspaces.models import MEMBERSHIP_MANAGER_ROLES, Role, WorkspaceMembership
from apps.workspaces.selectors import get_membership


def attach_workspace_membership(request: Request, membership: WorkspaceMembership) -> None:
    """DRF's Request has no `workspace_membership` attribute in its type
    stubs — this is the one place that adds it (IsWorkspaceMember calls
    it), so the `type: ignore` needed lives here instead of being
    repeated at every read site."""
    request.workspace_membership = membership  # type: ignore[attr-defined]


def get_workspace_membership(request: Request) -> WorkspaceMembership:
    """Read the membership IsWorkspaceMember (or a subclass) already
    verified and attached for this request. Only call this after that
    permission class has run — see attach_workspace_membership."""
    return request.workspace_membership  # type: ignore[attr-defined]


class IsWorkspaceMember(BasePermission):
    message = "You are not a member of this workspace."

    def has_permission(self, request: Request, view: APIView) -> bool:
        workspace_id = view.kwargs.get("workspace_id")
        if not workspace_id or not request.user or not request.user.is_authenticated:
            return False
        membership = get_membership(request.user, workspace_id)
        if membership is None:
            return False
        # Attach for the view/serializer to use — avoids a second query
        # and guarantees the role used downstream is the one just verified.
        attach_workspace_membership(request, membership)
        return True


class IsWorkspaceManager(IsWorkspaceMember):
    """Owner or Admin only — membership management, workspace settings."""

    message = "Only workspace owners and admins can do this."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not super().has_permission(request, view):
            return False
        return get_workspace_membership(request).role in MEMBERSHIP_MANAGER_ROLES


class IsWorkspaceOwner(IsWorkspaceMember):
    message = "Only the workspace owner can do this."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not super().has_permission(request, view):
            return False
        return get_workspace_membership(request).role == Role.OWNER
