"""In-app notifications, webhook endpoints (an "integration" in this
project's frontend), and signed webhook delivery records.

Encryption note: `WebhookEndpoint.secret` is the only genuinely
sensitive field this app stores, and it's encrypted at rest with
Fernet (see crypto.py) — the API never returns it once set (see
serializers.py). Everything else here (delivery payloads, notification
bodies) is deliberately kept to small, safe, non-sensitive content —
same retention discipline as apps.audit and apps.processing.
"""

import uuid

from django.conf import settings
from django.db import models

from apps.notifications.crypto import decrypt_secret, encrypt_secret


class Notification(models.Model):
    """One in-app notification for one user. The simplest of the three
    channels this app implements (in-app / email / webhook) — no
    delivery-retry concept, since it's just a database row the
    recipient reads on their own schedule."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="notifications"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    event_type = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    body = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "is_read", "-created_at"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notification({self.user_id}, {self.event_type})"


class WebhookEndpoint(models.Model):
    """A workspace-configured webhook — the "integration" a user sets up
    on the Integrations page. `is_simulated` is always True in this
    project (see docs/adr on simulated integrations): deliveries are
    real HTTP calls when a URL is configured, but this is a portfolio
    demo, not a certified/verified third-party integration, and the
    frontend must label it accordingly regardless of delivery success."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="webhook_endpoints"
    )
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=500)
    # Encrypted at rest (Fernet) — see crypto.py. Never exposed via the
    # API after creation; only used server-side to sign deliveries.
    encrypted_secret = models.BinaryField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["workspace", "is_active"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"WebhookEndpoint({self.name})"

    def set_secret(self, raw_secret: str) -> None:
        self.encrypted_secret = encrypt_secret(raw_secret)

    def get_secret(self) -> str:
        return decrypt_secret(bytes(self.encrypted_secret))


class WebhookDeliveryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class WebhookDelivery(models.Model):
    """One attempted delivery of one event to one endpoint.
    `idempotency_key` (event_type + endpoint + a caller-supplied
    dedupe key, e.g. a workflow run id) is unique, which is what makes
    re-dispatching the same event safe."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endpoint = models.ForeignKey(
        WebhookEndpoint, on_delete=models.CASCADE, related_name="deliveries"
    )
    event_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=16, choices=WebhookDeliveryStatus.choices, default=WebhookDeliveryStatus.PENDING
    )
    response_status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["endpoint", "-created_at"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"WebhookDelivery({self.endpoint_id}, {self.status})"
