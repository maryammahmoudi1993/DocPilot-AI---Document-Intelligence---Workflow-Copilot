from django.db.models import QuerySet

from apps.approvals.models import ApprovalRequest


def get_workspace_approvals(
    *, workspace_id: str, status: str | None = None
) -> QuerySet[ApprovalRequest]:
    queryset = ApprovalRequest.objects.filter(workspace_id=workspace_id).prefetch_related(
        "comments"
    )
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def get_workspace_approval(*, workspace_id: str, approval_id: str) -> ApprovalRequest | None:
    return (
        ApprovalRequest.objects.filter(workspace_id=workspace_id, id=approval_id)
        .prefetch_related("comments")
        .first()
    )
