from django.urls import path

from apps.documents.views import (
    DocumentArchiveView,
    DocumentBulkArchiveView,
    DocumentBulkDeleteView,
    DocumentDetailView,
    DocumentListCreateView,
)

urlpatterns = [
    path("", DocumentListCreateView.as_view(), name="document-list"),
    path("bulk-archive/", DocumentBulkArchiveView.as_view(), name="document-bulk-archive"),
    path("bulk-delete/", DocumentBulkDeleteView.as_view(), name="document-bulk-delete"),
    path("<uuid:document_id>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<uuid:document_id>/archive/", DocumentArchiveView.as_view(), name="document-archive"),
]
