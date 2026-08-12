from django.db.models import QuerySet

from apps.extraction.models import DocumentExtraction, ExtractionStatus


def get_workspace_extraction(*, workspace_id: str, document_id: str) -> DocumentExtraction | None:
    return (
        DocumentExtraction.objects.filter(workspace_id=workspace_id, document_id=document_id)
        .prefetch_related("fields", "issues")
        .first()
    )


def get_pending_review_extractions(*, workspace_id: str) -> QuerySet[DocumentExtraction]:
    """Backs the Review Queue: every extraction in this workspace still
    awaiting a decision, most recently created first."""
    return (
        DocumentExtraction.objects.filter(
            workspace_id=workspace_id, status=ExtractionStatus.PENDING_REVIEW
        )
        .select_related("document")
        .prefetch_related("issues")
        .order_by("-created_at")
    )
