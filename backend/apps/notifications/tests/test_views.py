import pytest
from django.urls import reverse

from apps.notifications.models import WebhookEndpoint
from apps.workspaces.models import Role
from tests.factories import (
    NotificationFactory,
    UserFactory,
    WebhookEndpointFactory,
    WorkspaceFactory,
    WorkspaceMembershipFactory,
)


@pytest.fixture
def workspace():
    return WorkspaceFactory()


def _client_with_role(api_client, workspace, role=Role.VIEWER):
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace, role=role)
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.mark.django_db
class TestNotificationListView:
    def test_only_returns_the_caller_s_own_notifications(self, api_client, workspace):
        _, user = _client_with_role(api_client, workspace)
        NotificationFactory(workspace=workspace, user=user, title="Mine")
        NotificationFactory(workspace=workspace, user=UserFactory(), title="Not mine")

        response = api_client.get(reverse("notifications:notification-list", args=[workspace.id]))

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["title"] == "Mine"

    def test_anonymous_is_rejected(self, api_client, workspace):
        response = api_client.get(reverse("notifications:notification-list", args=[workspace.id]))

        assert response.status_code == 401


@pytest.mark.django_db
class TestNotificationMarkReadView:
    def test_marks_the_caller_s_own_notification_as_read(self, api_client, workspace):
        _, user = _client_with_role(api_client, workspace)
        notification = NotificationFactory(workspace=workspace, user=user, is_read=False)

        response = api_client.post(
            reverse("notifications:notification-mark-read", args=[workspace.id, notification.id])
        )

        assert response.status_code == 200
        assert response.data["is_read"] is True

    def test_cannot_mark_another_user_s_notification_as_read(self, api_client, workspace):
        _client_with_role(api_client, workspace)
        notification = NotificationFactory(workspace=workspace, user=UserFactory())

        response = api_client.post(
            reverse("notifications:notification-mark-read", args=[workspace.id, notification.id])
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestWebhookEndpointListCreateView:
    def test_admin_can_create_an_endpoint_and_the_secret_is_never_returned(
        self, api_client, workspace
    ):
        _client_with_role(api_client, workspace, Role.ADMIN)

        response = api_client.post(
            reverse("integrations:webhook-endpoint-list", args=[workspace.id]),
            {"name": "My CRM", "url": "https://example.com/hook", "secret": "at-least-8-chars"},
            format="json",
        )

        assert response.status_code == 201
        assert "secret" not in response.data
        assert response.data["is_simulated"] is True
        endpoint = WebhookEndpoint.objects.get(id=response.data["id"])
        assert endpoint.get_secret() == "at-least-8-chars"

    def test_a_viewer_cannot_create_an_endpoint(self, api_client, workspace):
        _client_with_role(api_client, workspace, Role.VIEWER)

        response = api_client.post(
            reverse("integrations:webhook-endpoint-list", args=[workspace.id]),
            {"name": "My CRM", "url": "https://example.com/hook", "secret": "at-least-8-chars"},
            format="json",
        )

        assert response.status_code == 403

    def test_list_never_exposes_the_secret_field(self, api_client, workspace):
        WebhookEndpointFactory(workspace=workspace)
        _client_with_role(api_client, workspace)

        response = api_client.get(
            reverse("integrations:webhook-endpoint-list", args=[workspace.id])
        )

        assert response.status_code == 200
        assert all("secret" not in row for row in response.data)


@pytest.mark.django_db
class TestWebhookEndpointDetailView:
    def test_admin_can_delete_an_endpoint(self, api_client, workspace):
        endpoint = WebhookEndpointFactory(workspace=workspace)
        _client_with_role(api_client, workspace, Role.ADMIN)

        response = api_client.delete(
            reverse("integrations:webhook-endpoint-detail", args=[workspace.id, endpoint.id])
        )

        assert response.status_code == 204
        assert not WebhookEndpoint.objects.filter(id=endpoint.id).exists()

    def test_a_viewer_cannot_delete_an_endpoint(self, api_client, workspace):
        endpoint = WebhookEndpointFactory(workspace=workspace)
        _client_with_role(api_client, workspace, Role.VIEWER)

        response = api_client.delete(
            reverse("integrations:webhook-endpoint-detail", args=[workspace.id, endpoint.id])
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestWebhookDeliveryListView:
    def test_returns_404_for_an_endpoint_in_another_workspace(self, api_client, workspace):
        endpoint = WebhookEndpointFactory()
        _client_with_role(api_client, workspace)

        response = api_client.get(
            reverse("integrations:webhook-delivery-list", args=[workspace.id, endpoint.id])
        )

        assert response.status_code == 404
