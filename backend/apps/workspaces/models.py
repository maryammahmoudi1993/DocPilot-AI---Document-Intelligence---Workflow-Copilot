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
