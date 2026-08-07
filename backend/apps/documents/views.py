from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents import services
from apps.documents.models import Document
from apps.documents.selectors import get_workspace_documents
from apps.documents.serializers import (
    BulkActionSerializer,
    DocumentDetailSerializer,
    DocumentSerializer,
)
from apps.workspaces.models import Workspace
from apps.workspaces.permissions import IsWorkspaceMember


class DocumentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class DocumentListCreateView(APIView):
    permission_classes = [IsWorkspaceMember]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "content_type"]
    search_fields = ["filename"]
    ordering_fields = ["created_at", "size_bytes", "filename"]
    ordering = ["-created_at"]

    def get_queryset(self):
        # Not used by get() below directly (which already has
        # workspace_id from the URL kwarg) — exists so drf-spectacular's
        # DjangoFilterBackend introspection has a queryset to inspect for
        # schema generation; a plain APIView has no get_queryset() by default.
        return get_workspace_documents(self.kwargs.get("workspace_id"))

    @extend_schema(responses={200: DocumentSerializer(many=True)})
    def get(self, request: Request, workspace_id) -> Response:
        queryset = get_workspace_documents(workspace_id)
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)

        paginator = DocumentPagination()
        page: list[Document] | None = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(DocumentSerializer(page, many=True).data)

    @extend_schema(request=None, responses={201: DocumentSerializer})
    def post(self, request: Request, workspace_id) -> Response:
        workspace = get_object_or_404(Workspace, id=workspace_id)
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            raise ValidationError({"file": "No file provided."})

        document = services.create_document(
            workspace=workspace, uploaded_by=request.user, uploaded_file=uploaded_file
        )
        return Response(DocumentSerializer(document).data, status=201)


class DocumentDetailView(APIView):
    permission_classes = [IsWorkspaceMember]

    def _get_document(self, workspace_id, document_id) -> Document:
        # Scoped to workspace_id — a document_id from a different
        # workspace must 404, not be reachable through this URL (IDOR).
        return get_object_or_404(Document, id=document_id, workspace_id=workspace_id)

    @extend_schema(responses={200: DocumentDetailSerializer})
    def get(self, request: Request, workspace_id, document_id) -> Response:
        document = self._get_document(workspace_id, document_id)
        return Response(DocumentDetailSerializer(document).data)

    @extend_schema(request=None, responses={204: None})
    def delete(self, request: Request, workspace_id, document_id) -> Response:
        document = self._get_document(workspace_id, document_id)
        services.delete_document(document=document, actor=request.user)
        return Response(status=204)


class DocumentArchiveView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=None, responses={200: DocumentSerializer})
    def post(self, request: Request, workspace_id, document_id) -> Response:
        document = get_object_or_404(Document, id=document_id, workspace_id=workspace_id)
        updated = services.archive_document(document=document, actor=request.user)
        return Response(DocumentSerializer(updated).data)


class DocumentBulkArchiveView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=BulkActionSerializer, responses={200: DocumentSerializer(many=True)})
    def post(self, request: Request, workspace_id) -> Response:
        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace = get_object_or_404(Workspace, id=workspace_id)
        documents = services.bulk_archive(
            workspace=workspace,
            document_ids=serializer.validated_data["document_ids"],
            actor=request.user,
        )
        return Response(DocumentSerializer(documents, many=True).data)


class DocumentBulkDeleteView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=BulkActionSerializer, responses={204: None})
    def post(self, request: Request, workspace_id) -> Response:
        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace = get_object_or_404(Workspace, id=workspace_id)
        services.bulk_delete(
            workspace=workspace,
            document_ids=serializer.validated_data["document_ids"],
            actor=request.user,
        )
        return Response(status=204)
