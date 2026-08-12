"""Notification dispatch — in-app (synchronous, a plain row write),
email (log-only adapter, see providers note in the module docstring
below), and webhook (signed, idempotent, retried on failure via
Celery). Kept out of views/tasks per the project's non-negotiable rule.
"""

import logging
import secrets
from functools import partial

from django.db import transaction

from apps.notifications.models import Notification, WebhookDelivery, WebhookEndpoint

logger = logging.getLogger(__name__)


def _schedule_webhook_delivery(delivery_id: str) -> None:
    from apps.notifications.tasks import deliver_webhook

    deliver_webhook.delay(delivery_id)


def notify_user(
    *,
    user,
    workspace,
    title: str,
    body: str = "",
    event_type: str = "",
    metadata: dict | None = None,
) -> Notification:
    return Notification.objects.create(
        workspace=workspace,
        user=user,
        event_type=event_type,
        title=title,
        body=body,
        metadata=metadata or {},
    )


def notify_role(
    *,
    workspace,
    role: str,
    title: str,
    body: str = "",
    event_type: str = "",
    metadata: dict | None = None,
) -> list[Notification]:
    from apps.workspaces.selectors import get_workspace_members

    members = get_workspace_members(workspace.id).filter(role=role)
    return [
        notify_user(
            user=m.user,
            workspace=workspace,
            title=title,
            body=body,
            event_type=event_type,
            metadata=metadata,
        )
        for m in members
    ]


def get_user_notifications(*, workspace_id: str, user):
    """Untyped `user` param (vs. DRF's `request.user: User | AnonymousUser`)
    is the established project pattern for routing around a
    strictly-typed ORM lookup — see apps.workflows.services.create_workflow
    for the same fix applied to an identical mypy error."""
    return Notification.objects.filter(workspace_id=workspace_id, user=user)


@transaction.atomic
def create_webhook_endpoint(
    *, workspace, user, name: str, url: str, secret: str
) -> WebhookEndpoint:
    endpoint = WebhookEndpoint(workspace=workspace, name=name, url=url, created_by=user)
    endpoint.set_secret(secret)
    endpoint.save()
    return endpoint


def send_email(*, recipient: str, subject: str, body: str) -> None:
    """No real email provider is configured for this project (see
    docs/adr) — logging is the honest "real" behavior of this adapter
    until one is, exactly like apps.workflows.providers.HttpActionProvider's
    notification path. Never logs `body` in full (could contain
    workspace-specific context); only its length."""
    logger.info(
        "email_notification",
        extra={"recipient": recipient, "subject": subject, "body_length": len(body)},
    )


@transaction.atomic
def dispatch_webhook_event(
    *, workspace, event_type: str, payload: dict, dedupe_key: str
) -> list[WebhookDelivery]:
    """Creates one WebhookDelivery per active endpoint in the workspace
    and schedules each for delivery after commit. `dedupe_key` (e.g. a
    workflow run id) combined with the endpoint makes the resulting
    idempotency_key unique — calling this twice for the same event
    never double-delivers (the second call's get_or_create just returns
    the existing row, which the caller does not re-schedule)."""
    deliveries = []
    for endpoint in WebhookEndpoint.objects.filter(workspace=workspace, is_active=True):
        idempotency_key = f"{endpoint.id}:{event_type}:{dedupe_key}"
        delivery, created = WebhookDelivery.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={"endpoint": endpoint, "event_type": event_type, "payload": payload},
        )
        if created:
            deliveries.append(delivery)
            transaction.on_commit(partial(_schedule_webhook_delivery, str(delivery.id)))
    return deliveries


@transaction.atomic
def deliver_to_url(
    *, workspace, url: str, event_type: str, payload: dict, dedupe_key: str
) -> WebhookDelivery | None:
    """Direct one-URL delivery — what a workflow's `trigger_webhook`
    action node uses (its `url` config names one specific target,
    unlike `dispatch_webhook_event`'s workspace-wide subscriber fan-
    out). Auto-provisions a WebhookEndpoint for that URL on first use
    (with a random secret) so the delivery is still tracked and shows
    up in the Integrations page's delivery log like any other."""
    endpoint, _ = WebhookEndpoint.objects.get_or_create(
        workspace=workspace,
        url=url,
        defaults={"name": url, "encrypted_secret": b""},
    )
    if not endpoint.encrypted_secret:
        endpoint.set_secret(secrets.token_urlsafe(32))
        endpoint.save(update_fields=["encrypted_secret"])

    idempotency_key = f"{endpoint.id}:{event_type}:{dedupe_key}"
    delivery, created = WebhookDelivery.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={"endpoint": endpoint, "event_type": event_type, "payload": payload},
    )
    if created:
        transaction.on_commit(partial(_schedule_webhook_delivery, str(delivery.id)))
        return delivery
    return None
