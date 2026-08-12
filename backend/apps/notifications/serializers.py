from rest_framework import serializers

from apps.notifications.models import Notification, WebhookDelivery, WebhookEndpoint


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "event_type", "title", "body", "metadata", "is_read", "created_at"]
        read_only_fields = fields


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = [
            "id",
            "event_type",
            "status",
            "response_status_code",
            "attempt_count",
            "error_code",
            "created_at",
            "delivered_at",
        ]
        read_only_fields = fields


class WebhookEndpointSerializer(serializers.ModelSerializer):
    """`secret` is write-only and never present in any response — see
    WebhookEndpoint.encrypted_secret's docstring. `is_simulated` is a
    constant `True` so the frontend always shows the honest label
    regardless of whether real delivery is configured."""

    is_simulated = serializers.SerializerMethodField()

    class Meta:
        model = WebhookEndpoint
        fields = ["id", "name", "url", "is_active", "is_simulated", "created_at"]
        read_only_fields = fields

    def get_is_simulated(self, obj: WebhookEndpoint) -> bool:
        return True


class WebhookEndpointCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=1, max_length=255)
    url = serializers.URLField(max_length=500)
    secret = serializers.CharField(min_length=8, max_length=255, write_only=True)
