from django.urls import path

from apps.extraction.views import (
    DocumentExtractionDetailView,
    DocumentExtractionTransitionView,
    ExtractedFieldCorrectionView,
)

urlpatterns = [
    path("", DocumentExtractionDetailView.as_view(), name="document-extraction-detail"),
    path(
        "transition/",
        DocumentExtractionTransitionView.as_view(),
        name="document-extraction-transition",
    ),
    path(
        "fields/<uuid:field_id>/",
        ExtractedFieldCorrectionView.as_view(),
        name="document-extraction-field-correct",
    ),
]
