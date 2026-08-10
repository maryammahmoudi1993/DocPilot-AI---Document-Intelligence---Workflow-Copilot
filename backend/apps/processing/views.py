from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Document
from apps.processing import services
from apps.processing.serializers import ProcessingJobSerializer
from apps.workspaces.permissions import IsWorkspaceMember


class DocumentProcessingStatusView(APIView):
    """Progress/status endpoint — prefer polling for MVP (per the Phase 4
    prompt's technology direction), so this is a plain GET rather than
    SSE/WebSocket. Always reflects the *latest* job for the document,
    including a completed/failed one from a prior attempt."""

    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses={200: ProcessingJobSerializer})
    def get(self, request: Request, workspace_id, document_id) -> Response:
        document = get_object_or_404(Document, id=document_id, workspace_id=workspace_id)
        job = services.get_latest_processing_job(document=document)
        if job is None:
            raise NotFound("This document has not been queued for processing.")
        return Response(ProcessingJobSerializer(job).data)


class DocumentProcessingRetryView(APIView):
    """Authorized retry — any workspace member may retry (same
    membership-only bar as archive/delete in apps.documents.views;
    Phase 4 doesn't introduce a stricter role gate for this action)."""

    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=None, responses={201: ProcessingJobSerializer})
    def post(self, request: Request, workspace_id, document_id) -> Response:
        document = get_object_or_404(Document, id=document_id, workspace_id=workspace_id)
        # services.retry_processing raises Django's ValidationError (not
        # DRF's) when there's no retryable failed job — converted to the
        # stable {error:{...}} envelope by
        # common.exceptions.stable_exception_handler, same as every
        # apps.documents.services call site.
        job = services.retry_processing(document=document, actor=request.user)
        return Response(ProcessingJobSerializer(job).data, status=201)
