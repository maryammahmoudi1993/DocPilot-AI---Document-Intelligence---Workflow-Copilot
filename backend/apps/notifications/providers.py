"""Webhook delivery provider abstraction (project rule: mock external
providers at module boundaries; unit tests must never make a real
network call). `MockWebhookProvider` is the only one exercised in
tests; `HttpWebhookProvider` is a real, stdlib-only implementation for
a deployed environment."""

import hashlib
import hmac
import json
import urllib.error
import urllib.request
from typing import Protocol


class WebhookDeliveryError(Exception):
    """Normalized, retryable delivery failure (timeout, non-2xx, DNS/
    connection error)."""


class WebhookProvider(Protocol):
    def deliver(self, *, url: str, payload: dict, secret: str) -> int:
        """Returns the HTTP status code on success; raises
        WebhookDeliveryError on any failure."""
        ...


def sign_payload(*, payload_bytes: bytes, secret: str) -> str:
    """HMAC-SHA256 over the raw payload bytes — the same scheme
    countless real webhook providers (Stripe, GitHub) use, so it reads
    as a realistic, not merely illustrative, signature. Sent as the
    `X-DocPilot-Signature` header; a receiving service verifies it the
    same way (recompute and compare with hmac.compare_digest)."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


class MockWebhookProvider:
    """Deterministic — never touches the network. Always "succeeds"
    with a fixed status code, since what matters to this project's
    tests is that a delivery was attempted with the right signature and
    payload, not real HTTP behavior."""

    def deliver(self, *, url: str, payload: dict, secret: str) -> int:
        sign_payload(
            payload_bytes=json.dumps(payload, sort_keys=True).encode("utf-8"), secret=secret
        )
        return 200


class HttpWebhookProvider:
    """Real implementation — stdlib-only (urllib), no new dependency.
    Not covered by unit tests (would violate the no-external-calls rule);
    exists so NOTIFICATION_WEBHOOK_PROVIDER=http is a real, working
    option in a deployed environment, not just a placeholder."""

    def deliver(self, *, url: str, payload: dict, secret: str) -> int:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = sign_payload(payload_bytes=body, secret=secret)
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "X-DocPilot-Signature": signature},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
                return response.status
        except (urllib.error.URLError, TimeoutError) as exc:
            raise WebhookDeliveryError(str(exc)) from exc


def get_webhook_provider() -> WebhookProvider:
    from django.conf import settings

    if settings.NOTIFICATION_WEBHOOK_PROVIDER == "http":
        return HttpWebhookProvider()
    return MockWebhookProvider()
