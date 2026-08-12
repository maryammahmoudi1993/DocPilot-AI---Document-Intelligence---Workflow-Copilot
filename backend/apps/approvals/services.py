"""Approval-request business logic — kept out of views/tasks per the
project's non-negotiable rule. Two things matter most:

- `decide` is idempotent: repeating the *same* decision on an
  already-decided request is a safe no-op (never a duplicate
  notification/webhook); attempting a *different* decision than the one
  already recorded is rejected as an invalid transition.
- Expiration is evaluated lazily (on decide/read), not via a scheduled
  task — simpler and just as correct for this project's scale, and
  avoids Celery Beat wiring "where scheduling is[not] required" (see
  the project's tech-direction note that Beat is for where it's
  actually needed).
"""

from django.db import transaction
from django.utils import timezone

from apps.approvals.exceptions import InvalidApprovalTransitionError
from apps.approvals.models import ApprovalComment, ApprovalRequest, ApprovalStatus
from apps.audit.services import record_event


@transaction.atomic
def create_approval_request(
    *,
    workspace,
    title: str,
    description: str = "",
    risk_level: str = "low",
    assigned_role: str = "admin",
    document=None,
    document_id: str | None = None,
    workflow_run=None,
    requested_by=None,
    expires_at=None,
) -> ApprovalRequest:
    if document is None and document_id:
        from apps.documents.models import Document

        document = Document.objects.filter(id=document_id).first()

    approval = ApprovalRequest.objects.create(
        workspace=workspace,
        document=document,
        workflow_run=workflow_run,
        title=title,
        description=description,
        risk_level=risk_level,
        assigned_role=assigned_role,
        requested_by=requested_by,
        expires_at=expires_at,
    )
    record_event(
        event_type="approval.requested",
        actor=requested_by,
        workspace=workspace,
        metadata={"approval_id": str(approval.id), "title": title, "risk_level": risk_level},
    )

    from apps.notifications.services import notify_role

    notify_role(
        workspace=workspace,
        role=assigned_role,
        title="Approval requested",
        body=title,
        event_type="approval.requested",
        metadata={"approval_id": str(approval.id)},
    )
    return approval


def _apply_expiry(approval: ApprovalRequest) -> ApprovalRequest:
    if approval.status == ApprovalStatus.PENDING and approval.is_expired:
        approval.status = ApprovalStatus.EXPIRED
        approval.save(update_fields=["status", "updated_at"])
    return approval


@transaction.atomic
def decide(
    *, approval: ApprovalRequest, new_status: str, user, reason: str = ""
) -> ApprovalRequest:
    approval = ApprovalRequest.objects.select_for_update().get(id=approval.id)
    approval = _apply_expiry(approval)

    if approval.status != ApprovalStatus.PENDING:
        if approval.status == new_status:
            # Repeating the same decision (e.g. a double-click or a
            # retried request) is a safe no-op, not an error.
            return approval
        raise InvalidApprovalTransitionError(f"Cannot move from {approval.status} to {new_status}.")

    if new_status not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
        raise InvalidApprovalTransitionError(f"{new_status} is not a valid decision.")

    approval.status = new_status
    approval.decided_by = user
    approval.decided_at = timezone.now()
    approval.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])

    if reason:
        ApprovalComment.objects.create(approval=approval, author=user, body=reason)

    record_event(
        event_type=f"approval.{new_status}",
        actor=user,
        workspace=approval.workspace,
        metadata={"approval_id": str(approval.id)},
    )

    from apps.notifications.services import notify_user

    if approval.requested_by:
        notify_user(
            user=approval.requested_by,
            workspace=approval.workspace,
            title=f"Approval {new_status}",
            body=approval.title,
            event_type=f"approval.{new_status}",
            metadata={"approval_id": str(approval.id)},
        )
    return approval


def add_comment(*, approval: ApprovalRequest, author, body: str) -> ApprovalComment:
    comment = ApprovalComment.objects.create(approval=approval, author=author, body=body)
    record_event(
        event_type="approval.commented",
        actor=author,
        workspace=approval.workspace,
        metadata={"approval_id": str(approval.id)},
    )
    return comment
