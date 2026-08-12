"""High-value approval requests — created by the workflow engine's
`request_approval` action (see apps.workflows.services._handle_request_approval)
or, in principle, any future caller. Distinct from apps.extraction's
document-approval transition: that's "is this extraction correct", this
is "should this high-value action proceed" (e.g. an invoice over a
threshold), and can exist without an extraction at all."""

import uuid

from django.conf import settings
from django.db import models


class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    EXPIRED = "expired", "Expired"


class RiskLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class ApprovalRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="approval_requests"
    )
    document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approval_requests",
    )
    # Nullable: an approval can be requested manually in principle, not
    # only by a workflow run — see apps.workflows.services request_approval.
    workflow_run = models.ForeignKey(
        "workflows.WorkflowRun",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approval_requests",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    risk_level = models.CharField(max_length=16, choices=RiskLevel.choices, default=RiskLevel.LOW)
    status = models.CharField(
        max_length=16, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )
    # A role, not a specific user — matches the workflow node's
    # `approver_role` config (see apps.workflows.providers). Any member
    # holding that role in this workspace may act on the request.
    assigned_role = models.CharField(max_length=32, default="admin")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "status", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ApprovalRequest({self.title}, {self.status})"

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        from django.utils import timezone

        return self.status == ApprovalStatus.PENDING and timezone.now() >= self.expires_at


class ApprovalComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    approval = models.ForeignKey(ApprovalRequest, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    body = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["approval", "created_at"])]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"ApprovalComment({self.approval_id})"
