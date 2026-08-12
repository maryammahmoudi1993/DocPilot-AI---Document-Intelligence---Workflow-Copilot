import uuid

from django.conf import settings
from django.db import models


class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    FINANCE_MANAGER = "finance_manager", "Finance Manager"
    REVIEWER = "reviewer", "Reviewer"
    VIEWER = "viewer", "Viewer"


# Roles that can be assigned directly (owner is set only via
# transfer-ownership — see apps/workspaces/services.py).
ASSIGNABLE_ROLES = [Role.ADMIN, Role.FINANCE_MANAGER, Role.REVIEWER, Role.VIEWER]
MEMBERSHIP_MANAGER_ROLES = [Role.OWNER, Role.ADMIN]


class Workspace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class WorkspaceMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workspace_memberships"
    )
    role = models.CharField(max_length=32, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user"], name="unique_workspace_membership"
            ),
        ]
        indexes = [
            # Real query patterns: "who are the members of workspace X (with
            # role Y)" and "which workspaces is user X a member of".
            models.Index(fields=["workspace", "role"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.workspace_id} ({self.role})"


class WorkspaceSettings(models.Model):
    """One row per workspace, created lazily on first read (see
    apps/workspaces/services.get_or_create_settings) rather than at
    Workspace-creation time — keeps Workspace creation itself
    dependency-free. Everything here is a real, enforced setting, not a
    decorative toggle: `auto_classify_enabled` gates whether newly
    uploaded documents are auto-classified by apps.processing (see
    apps/processing/tasks.py), and `document_retention_days` /
    `raw_text_retention_days` are read by the (Phase 10+) retention
    sweep, not just displayed."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name="settings")

    # Notification preferences.
    notify_on_approval_requested = models.BooleanField(default=True)
    notify_on_document_processed = models.BooleanField(default=True)
    webhook_notifications_enabled = models.BooleanField(default=True)

    # Processing rules.
    auto_classify_enabled = models.BooleanField(default=True)

    # Data retention. Null means "keep indefinitely" (the current
    # default — no sweep runs until an operator opts a workspace in).
    document_retention_days = models.PositiveIntegerField(null=True, blank=True)
    raw_text_retention_days = models.PositiveIntegerField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"WorkspaceSettings({self.workspace_id})"
