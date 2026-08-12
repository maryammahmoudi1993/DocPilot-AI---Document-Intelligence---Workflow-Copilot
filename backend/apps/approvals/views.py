from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.approvals import services
from apps.approvals.selectors import get_workspace_approval, get_workspace_approvals
from apps.approvals.serializers import (
    ApprovalCommentRequestSerializer,
    ApprovalCommentSerializer,
    ApprovalDecisionRequestSerializer,
    ApprovalRequestSerializer,
)
from apps.workspaces.models import Role
from apps.workspaces.permissions import IsWorkspaceMember, get_workspace_membership

# Owner/admin can always decide (so a request never gets permanently
# stuck if the specific assigned_role has no active members); otherwise
# the caller's role must match the request's assigned_role exactly.
_ALWAYS_CAN_DECIDE_ROLES = {Role.OWNER, Role.ADMIN}


class ApprovalListView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses=ApprovalRequestSerializer(many=True))
    def get(self, request: Request, workspace_id: str) -> Response:
        status_filter = request.query_params.get("status")
        approvals = get_workspace_approvals(workspace_id=workspace_id, status=status_filter)
        return Response(ApprovalRequestSerializer(approvals, many=True).data)


class ApprovalDetailView(APIView):
    permission_classes = [IsWorkspaceMember]

    def _get(self, workspace_id: str, approval_id: str):
        approval = get_workspace_approval(workspace_id=workspace_id, approval_id=approval_id)
        if approval is None:
            raise NotFound("Approval request not found.")
        return approval

    @extend_schema(responses=ApprovalRequestSerializer)
    def get(self, request: Request, workspace_id: str, approval_id: str) -> Response:
        return Response(ApprovalRequestSerializer(self._get(workspace_id, approval_id)).data)


class ApprovalDecisionView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=ApprovalDecisionRequestSerializer, responses=ApprovalRequestSerializer)
    def post(self, request: Request, workspace_id: str, approval_id: str) -> Response:
        approval = get_workspace_approval(workspace_id=workspace_id, approval_id=approval_id)
        if approval is None:
            raise NotFound("Approval request not found.")

        membership = get_workspace_membership(request)
        if (
            membership.role not in _ALWAYS_CAN_DECIDE_ROLES
            and membership.role != approval.assigned_role
        ):
            raise PermissionDenied("You are not authorized to decide this approval request.")

        payload = ApprovalDecisionRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        approval = services.decide(
            approval=approval,
            new_status=payload.validated_data["status"],
            user=request.user,
            reason=payload.validated_data["reason"],
        )
        return Response(ApprovalRequestSerializer(approval).data)


class ApprovalCommentListCreateView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=ApprovalCommentRequestSerializer, responses=ApprovalCommentSerializer)
    def post(self, request: Request, workspace_id: str, approval_id: str) -> Response:
        approval = get_workspace_approval(workspace_id=workspace_id, approval_id=approval_id)
        if approval is None:
            raise NotFound("Approval request not found.")

        payload = ApprovalCommentRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        comment = services.add_comment(
            approval=approval, author=request.user, body=payload.validated_data["body"]
        )
        return Response(ApprovalCommentSerializer(comment).data, status=201)
