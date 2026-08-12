from django.urls import path

from apps.notifications.views import (
    NotificationListView,
    NotificationMarkReadView,
    WebhookDeliveryListView,
    WebhookEndpointDetailView,
    WebhookEndpointListCreateView,
)

notification_urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path(
        "<uuid:notification_id>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),
]

integration_urlpatterns = [
    path("", WebhookEndpointListCreateView.as_view(), name="webhook-endpoint-list"),
    path(
        "<uuid:endpoint_id>/", WebhookEndpointDetailView.as_view(), name="webhook-endpoint-detail"
    ),
    path(
        "<uuid:endpoint_id>/deliveries/",
        WebhookDeliveryListView.as_view(),
        name="webhook-delivery-list",
    ),
]
