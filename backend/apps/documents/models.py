import uuid

from django.conf import settings
from django.db import models


class DocumentStatus(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    ARCHIVED = "archived", "Archived"


class Document(models.Model):
    """A single uploaded file, private in object storage — see
    apps/documents/storage.py. Never a business-logic-bearing model
    itself (see services.py for the state-machine transitions and
    upload/validation logic — kept out of the model per the project's
    non-negotiable rule keeping business logic out of thin layers)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="documents"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    checksum_sha256 = models.CharField(max_length=64)
    # Object storage key — never exposed directly to the client; only a
    # short-lived signed URL derived from it is (see storage.py).
    storage_key = models.CharField(max_length=512, unique=True)
    status = models.CharField(
        max_length=16, choices=DocumentStatus.choices, default=DocumentStatus.UPLOADED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            # Real query patterns: "list workspace X's documents, newest
            # first, optionally filtered by status" and "does workspace X
            # already have a document with this checksum" (duplicate
            # detection).
            models.Index(fields=["workspace", "status", "-created_at"]),
            models.Index(fields=["workspace", "checksum_sha256"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.filename
