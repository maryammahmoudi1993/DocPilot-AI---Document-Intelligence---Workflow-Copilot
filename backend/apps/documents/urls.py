from django.urls import path

from apps.documents.views import (
    DocumentArchiveView,
    DocumentBulkArchiveView,
    DocumentBulkDeleteView,
    DocumentDetailView,
    DocumentListCreateView,
)
from apps.processing.views import DocumentProcessingRetryView, DocumentProcessingStatusView

urlpatterns = [
    path("", DocumentListCreateView.as_view(), name="document-list"),
    path("bulk-archive/", DocumentBulkArchiveView.as_view(), name="document-bulk-archive"),
    path("bulk-delete/", DocumentBulkDeleteView.as_view(), name="document-bulk-delete"),
    path("<uuid:document_id>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<uuid:document_id>/archive/", DocumentArchiveView.as_view(), name="document-archive"),
    # Document-scoped, so they live under apps.documents.urls rather than
    # a separate apps.processing prefix — a processing job only ever
    # makes sense in the context of the document it belongs to.
    path(
        "<uuid:document_id>/processing/",
        DocumentProcessingStatusView.as_view(),
        name="document-processing-status",
    ),
    path(
        "<uuid:document_id>/processing/retry/",
        DocumentProcessingRetryView.as_view(),
        name="document-processing-retry",
    ),
]
