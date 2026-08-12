from typing import cast

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.workspaces import services
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.workspaces.permissions import (
    IsWorkspaceManager,
    IsWorkspaceMember,
    IsWorkspaceOwner,
    get_workspace_membership,
)
from apps.workspaces.selectors import get_user_workspaces, get_workspace_members
from apps.workspaces.serializers import (
    AddMemberSerializer,
    ChangeRoleSerializer,
    MembershipSerializer,
    TransferOwnershipSerializer,
    WorkspaceSerializer,
    WorkspaceSettingsSerializer,
    WorkspaceSettingsUpdateSerializer,
)


class WorkspaceListView(APIView):
    """Every workspace the caller is a member of — never any others."""

    @extend_schema(responses={200: WorkspaceSerializer(many=True)})
    def get(self, request: Request) -> Response:
        # IsAuthenticated (the default permission) guarantees request.user
        # is a real User, not AnonymousUser, by the time this runs.
        workspaces = get_user_workspaces(cast(User, request.user))
        return Response(WorkspaceSerializer(workspaces, many=True).data)


class MembershipListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsWorkspaceManager()]
        return [IsWorkspaceMember()]

    @extend_schema(responses={200: MembershipSerializer(many=True)})
    def get(self, request: Request, workspace_id) -> Response:
        members = get_workspace_members(workspace_id)
        return Response(MembershipSerializer(members, many=True).data)

    @extend_schema(request=AddMemberSerializer, responses={201: MembershipSerializer})
    def post(self, request: Request, workspace_id) -> Response:
        workspace = get_object_or_404(Workspace, id=workspace_id)
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.add_member(
            workspace=workspace,
            actor_membership=get_workspace_membership(request),
            **serializer.validated_data,
        )
        return Response(MembershipSerializer(membership).data, status=201)


class MembershipDetailView(APIView):
    permission_classes = [IsWorkspaceManager]

    def _get_membership(self, workspace_id, membership_id) -> WorkspaceMembership:
        # Scoped to workspace_id — a membership_id from a different
        # workspace must 404, not be editable via this URL.
        return get_object_or_404(WorkspaceMembership, id=membership_id, workspace_id=workspace_id)

    @extend_schema(request=ChangeRoleSerializer, responses={200: MembershipSerializer})
    def patch(self, request: Request, workspace_id, membership_id) -> Response:
        membership = self._get_membership(workspace_id, membership_id)
        serializer = ChangeRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = services.change_role(
            membership=membership,
            actor_membership=get_workspace_membership(request),
            new_role=serializer.validated_data["role"],
        )
        return Response(MembershipSerializer(updated).data)

    @extend_schema(request=None, responses={204: None})
    def delete(self, request: Request, workspace_id, membership_id) -> Response:
        membership = self._get_membership(workspace_id, membership_id)
        services.remove_member(
            membership=membership, actor_membership=get_workspace_membership(request)
        )
        return Response(status=204)


class WorkspaceSettingsView(APIView):
    """GET is available to any member (settings inform what they should
    expect, e.g. retention); PATCH is manager-only (see
    IsWorkspaceManager)."""

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsWorkspaceManager()]
        return [IsWorkspaceMember()]

    @extend_schema(responses={200: WorkspaceSettingsSerializer})
    def get(self, request: Request, workspace_id) -> Response:
        workspace = get_object_or_404(Workspace, id=workspace_id)
        settings_row = services.get_or_create_settings(workspace=workspace)
        return Response(WorkspaceSettingsSerializer(settings_row).data)

    @extend_schema(
        request=WorkspaceSettingsUpdateSerializer, responses={200: WorkspaceSettingsSerializer}
    )
    def patch(self, request: Request, workspace_id) -> Response:
        workspace = get_object_or_404(Workspace, id=workspace_id)
        serializer = WorkspaceSettingsUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        settings_row = services.update_settings(
            workspace=workspace,
            actor_membership=get_workspace_membership(request),
            **serializer.validated_data,
        )
        return Response(WorkspaceSettingsSerializer(settings_row).data)


class TransferOwnershipView(APIView):
    permission_classes = [IsWorkspaceOwner]

    @extend_schema(request=TransferOwnershipSerializer, responses={204: None})
    def post(self, request: Request, workspace_id) -> Response:
        workspace = get_object_or_404(Workspace, id=workspace_id)
        serializer = TransferOwnershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_owner_membership = get_object_or_404(
            WorkspaceMembership,
            id=serializer.validated_data["new_owner_membership_id"],
            workspace_id=workspace_id,
        )
        services.transfer_ownership(
            workspace=workspace,
            current_owner_membership=get_workspace_membership(request),
            new_owner_membership=new_owner_membership,
        )
        return Response(status=204)
