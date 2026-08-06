import uuid

from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """Immutable log of security- and workspace-relevant actions.

    Deliberately append-only at the application layer — nothing in this
    codebase updates or deletes an AuditEvent. `metadata` must never
    contain secrets, tokens, passwords, or full document contents (see
    the project-wide logging rule); it holds small, structured, non-
    sensitive context (e.g. which role was assigned, not a password).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    event_type = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event_type} @ {self.created_at.isoformat()}"
