"""Celery task delivering one WebhookDelivery — mirrors the retry/
idempotency shape apps.processing.tasks and apps.workflows.tasks
already established: bind=True with a small fixed attempt cap,
exponential backoff, and a safe no-op for a missing or already-terminal
delivery (Celery's at-least-once redelivery)."""

import logging

from celery import shared_task
from django.utils import timezone

from apps.notifications.models import WebhookDelivery, WebhookDeliveryStatus
from apps.notifications.providers import WebhookDeliveryError, get_webhook_provider

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


@shared_task(bind=True, max_retries=MAX_ATTEMPTS - 1)
def deliver_webhook(self, delivery_id: str) -> None:  # noqa: ANN001 - Celery binds `self`
    try:
        delivery = WebhookDelivery.objects.select_related("endpoint").get(id=delivery_id)
    except WebhookDelivery.DoesNotExist:
        logger.warning("webhook_delivery_not_found", extra={"delivery_id": delivery_id})
        return

    if delivery.status != WebhookDeliveryStatus.PENDING:
        return

    delivery.attempt_count += 1
    try:
        status_code = get_webhook_provider().deliver(
            url=delivery.endpoint.url,
            payload=delivery.payload,
            secret=delivery.endpoint.get_secret(),
        )
        delivery.status = WebhookDeliveryStatus.SUCCEEDED
        delivery.response_status_code = status_code
        delivery.delivered_at = timezone.now()
        delivery.save(
            update_fields=["status", "response_status_code", "delivered_at", "attempt_count"]
        )
    except WebhookDeliveryError as exc:
        delivery.error_code = "provider_unavailable"
        if self.request.retries < MAX_ATTEMPTS - 1:
            delivery.save(update_fields=["attempt_count", "error_code"])
            raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
        delivery.status = WebhookDeliveryStatus.FAILED
        delivery.save(update_fields=["status", "error_code", "attempt_count"])
        logger.warning("webhook_delivery_failed", extra={"delivery_id": str(delivery.id)})
