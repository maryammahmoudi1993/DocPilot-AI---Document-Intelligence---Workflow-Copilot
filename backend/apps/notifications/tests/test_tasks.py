import pytest

from apps.notifications.models import WebhookDelivery, WebhookDeliveryStatus
from apps.notifications.providers import WebhookDeliveryError
from apps.notifications.tasks import MAX_ATTEMPTS, deliver_webhook
from tests.factories import WebhookEndpointFactory


@pytest.mark.django_db
def test_a_missing_delivery_id_is_a_safe_no_op():
    deliver_webhook.delay("00000000-0000-0000-0000-000000000000")  # must not raise


@pytest.mark.django_db
def test_a_delivery_already_past_pending_is_a_safe_no_op():
    endpoint = WebhookEndpointFactory()
    delivery = WebhookDelivery.objects.create(
        endpoint=endpoint,
        event_type="test.event",
        idempotency_key="already-delivered",
        status=WebhookDeliveryStatus.SUCCEEDED,
    )

    deliver_webhook.delay(str(delivery.id))

    delivery.refresh_from_db()
    assert delivery.attempt_count == 0  # never re-attempted


@pytest.mark.django_db
def test_a_successful_delivery_records_status_code_and_timestamp():
    endpoint = WebhookEndpointFactory()
    delivery = WebhookDelivery.objects.create(
        endpoint=endpoint,
        event_type="test.event",
        idempotency_key="delivery-1",
        payload={"a": 1},
    )

    deliver_webhook.delay(str(delivery.id))

    delivery.refresh_from_db()
    assert delivery.status == WebhookDeliveryStatus.SUCCEEDED
    assert delivery.response_status_code == 200
    assert delivery.delivered_at is not None
    assert delivery.attempt_count == 1


@pytest.mark.django_db
def test_a_provider_failure_retries_then_marks_failed_after_the_attempt_cap(monkeypatch):
    endpoint = WebhookEndpointFactory()
    delivery = WebhookDelivery.objects.create(
        endpoint=endpoint,
        event_type="test.event",
        idempotency_key="delivery-2",
    )

    def _always_fails(self, *, url, payload, secret):
        raise WebhookDeliveryError("simulated timeout")

    monkeypatch.setattr(
        "apps.notifications.tasks.get_webhook_provider",
        lambda: type("FailingProvider", (), {"deliver": _always_fails})(),
    )

    deliver_webhook.delay(str(delivery.id))

    delivery.refresh_from_db()
    assert delivery.status == WebhookDeliveryStatus.FAILED
    assert delivery.error_code == "provider_unavailable"
    assert delivery.attempt_count == MAX_ATTEMPTS
