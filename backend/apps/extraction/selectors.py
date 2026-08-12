from apps.extraction.models import DocumentExtraction


def get_workspace_extraction(*, workspace_id: str, document_id: str) -> DocumentExtraction | None:
    return (
        DocumentExtraction.objects.filter(workspace_id=workspace_id, document_id=document_id)
        .prefetch_related("fields", "issues")
        .first()
    )
