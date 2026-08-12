from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Document
from apps.extraction import services
from apps.extraction.models import ExtractedField
from apps.extraction.selectors import get_pending_review_extractions, get_workspace_extraction
from apps.extraction.serializers import (
    DocumentExtractionSerializer,
    ExtractedFieldSerializer,
    ExtractionQueueItemSerializer,
    FieldCorrectionRequestSerializer,
    StatusTransitionRequestSerializer,
)
from apps.workspaces.models import Role
from apps.workspaces.permissions import IsWorkspaceMember, get_workspace_membership

# Reviewer and above can correct fields; viewer cannot.
_CAN_CORRECT_ROLES = {Role.OWNER, Role.ADMIN, Role.FINANCE_MANAGER, Role.REVIEWER}
# Only finance/admin/owner can give final approval — matches the
# "high-value approval" role in the primary demo flow.
_CAN_APPROVE_ROLES = {Role.OWNER, Role.ADMIN, Role.FINANCE_MANAGER}


class ExtractionQueueView(APIView):
    """Workspace-wide Review Queue — every extraction still awaiting a
    decision. Deliberately unpaginated (demo-scale: a handful of pending
    invoices, not a production-scale backlog)."""

    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses=ExtractionQueueItemSerializer(many=True))
    def get(self, request: Request, workspace_id: str) -> Response:
        extractions = get_pending_review_extractions(workspace_id=workspace_id)
        return Response(ExtractionQueueItemSerializer(extractions, many=True).data)


class DocumentExtractionDetailView(APIView):
    permission_classes = [IsWorkspaceMember]

    def _get_extraction(self, workspace_id: str, document_id: str):
        get_object_or_404(Document, id=document_id, workspace_id=workspace_id)
        extraction = get_workspace_extraction(workspace_id=workspace_id, document_id=document_id)
        if extraction is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("No extraction exists for this document yet.")
        return extraction

    @extend_schema(responses=DocumentExtractionSerializer)
    def get(self, request: Request, workspace_id: str, document_id: str) -> Response:
        extraction = self._get_extraction(workspace_id, document_id)
        return Response(DocumentExtractionSerializer(extraction).data)


class ExtractedFieldCorrectionView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=FieldCorrectionRequestSerializer, responses=ExtractedFieldSerializer)
    def patch(
        self, request: Request, workspace_id: str, document_id: str, field_id: str
    ) -> Response:
        from rest_framework.exceptions import PermissionDenied

        membership = get_workspace_membership(request)
        if membership.role not in _CAN_CORRECT_ROLES:
            raise PermissionDenied("You do not have permission to correct extracted fields.")

        field = get_object_or_404(
            ExtractedField,
            id=field_id,
            extraction__workspace_id=workspace_id,
            extraction__document_id=document_id,
        )
        payload = FieldCorrectionRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        field = services.correct_field(
            field=field,
            user=request.user,
            value=payload.validated_data["value"],
            reason=payload.validated_data["reason"],
            expected_version=payload.validated_data["expected_version"],
        )
        field.refresh_from_db()
        return Response(ExtractedFieldSerializer(field).data)


class DocumentExtractionTransitionView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(
        request=StatusTransitionRequestSerializer, responses=DocumentExtractionSerializer
    )
    def post(self, request: Request, workspace_id: str, document_id: str) -> Response:
        from rest_framework.exceptions import PermissionDenied

        membership = get_workspace_membership(request)
        payload = StatusTransitionRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        new_status = payload.validated_data["status"]

        if new_status == "approved" and membership.role not in _CAN_APPROVE_ROLES:
            raise PermissionDenied("You do not have permission to approve this extraction.")
        if (
            new_status in {"rejected", "pending_review"}
            and membership.role not in _CAN_CORRECT_ROLES
        ):
            raise PermissionDenied("You do not have permission to change this extraction's status.")

        get_object_or_404(Document, id=document_id, workspace_id=workspace_id)
        extraction = get_workspace_extraction(workspace_id=workspace_id, document_id=document_id)
        if extraction is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("No extraction exists for this document yet.")

        extraction = services.transition_status(
            extraction=extraction,
            new_status=new_status,
            user=request.user,
            expected_version=payload.validated_data["expected_version"],
        )
        return Response(DocumentExtractionSerializer(extraction).data)
