from apps.documents.models import Document


def get_workspace_documents(workspace_id):
    """The authoritative workspace-scoped document queryset — every view
    goes through this rather than querying Document directly, so a
    document from another workspace can never leak into a list or a
    lookup by id+workspace_id."""
    return Document.objects.filter(workspace_id=workspace_id).select_related("uploaded_by")
