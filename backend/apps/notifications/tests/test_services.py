import pytest

from apps.notifications import services
from apps.notifications.models import Notification, WebhookDelivery, WebhookEndpoint
from apps.workspaces.models import Role
from tests.factories import (
    UserFactory,
    WebhookEndpointFactory,
    WorkspaceFactory,
    WorkspaceMembershipFactory,
)


@pytest.mark.django_db
class TestNotifyUserAndRole:
    def test_notify_user_creates_one_row(self):
        workspace = WorkspaceFactory()
        user = UserFactory()

        notification = services.notify_user(
            user=user, workspace=workspace, title="Hello", event_type="test.event"
        )

        assert Notification.objects.filter(id=notification.id, user=user).exists()

    def test_notify_role_reaches_every_member_holding_that_role(self):
        workspace = WorkspaceFactory()
        admin_a = UserFactory()
        admin_b = UserFactory()
        viewer = UserFactory()
        WorkspaceMembershipFactory(user=admin_a, workspace=workspace, role=Role.ADMIN)
        WorkspaceMembershipFactory(user=admin_b, workspace=workspace, role=Role.ADMIN)
        WorkspaceMembershipFactory(user=viewer, workspace=workspace, role=Role.VIEWER)

        notifications = services.notify_role(
            workspace=workspace, role=Role.ADMIN, title="Approval requested"
        )

        assert {n.user_id for n in notifications} == {admin_a.id, admin_b.id}


@pytest.mark.django_db
class TestGetUserNotifications:
    def test_scoped_to_workspace_and_user(self):
        workspace = WorkspaceFactory()
        user = UserFactory()
        other_user = UserFactory()
        services.notify_user(user=user, workspace=workspace, title="Mine")
        services.notify_user(user=other_user, workspace=workspace, title="Not mine")

        results = services.get_user_notifications(workspace_id=workspace.id, user=user)

        assert results.count() == 1
        assert results.first().title == "Mine"


@pytest.mark.django_db
class TestCreateWebhookEndpoint:
    def test_encrypts_the_secret_and_never_stores_it_in_plaintext(self):
        workspace = WorkspaceFactory()
        user = UserFactory()

        endpoint = services.create_webhook_endpoint(
            workspace=workspace,
            user=user,
            name="My endpoint",
            url="https://example.com/hook",
            secret="super-secret-value",
        )

        assert endpoint.encrypted_secret != b"super-secret-value"
        assert b"super-secret-value" not in bytes(endpoint.encrypted_secret)
        assert endpoint.get_secret() == "super-secret-value"


@pytest.mark.django_db
class TestDispatchWebhookEvent:
    def test_creates_one_delivery_per_active_endpoint(self, django_capture_on_commit_callbacks):
        workspace = WorkspaceFactory()
        WebhookEndpointFactory(workspace=workspace)
        WebhookEndpointFactory(workspace=workspace)
        WebhookEndpointFactory(workspace=workspace, is_active=False)

        with django_capture_on_commit_callbacks(execute=True):
            deliveries = services.dispatch_webhook_event(
                workspace=workspace,
                event_type="document.processed",
                payload={"document_id": "abc"},
                dedupe_key="dedupe-1",
            )

        assert len(deliveries) == 2
        assert WebhookDelivery.objects.filter(status="succeeded").count() == 2

    def test_redispatching_the_same_event_never_double_delivers(
        self, django_capture_on_commit_callbacks
    ):
        workspace = WorkspaceFactory()
        WebhookEndpointFactory(workspace=workspace)

        with django_capture_on_commit_callbacks(execute=True):
            services.dispatch_webhook_event(
                workspace=workspace,
                event_type="document.processed",
                payload={},
                dedupe_key="same-key",
            )
        with django_capture_on_commit_callbacks(execute=True):
            second = services.dispatch_webhook_event(
                workspace=workspace,
                event_type="document.processed",
                payload={},
                dedupe_key="same-key",
            )

        assert second == []
        assert WebhookDelivery.objects.count() == 1


@pytest.mark.django_db
class TestDeliverToUrl:
    def test_auto_provisions_an_endpoint_for_a_new_url(self, django_capture_on_commit_callbacks):
        workspace = WorkspaceFactory()

        with django_capture_on_commit_callbacks(execute=True):
            delivery = services.deliver_to_url(
                workspace=workspace,
                url="https://example.com/webhook-target",
                event_type="workflow.webhook",
                payload={"event": "x"},
                dedupe_key="run-1",
            )

        assert delivery is not None
        assert WebhookEndpoint.objects.filter(
            workspace=workspace, url="https://example.com/webhook-target"
        ).exists()

    def test_reusing_the_same_url_and_dedupe_key_returns_none_the_second_time(
        self, django_capture_on_commit_callbacks
    ):
        workspace = WorkspaceFactory()

        with django_capture_on_commit_callbacks(execute=True):
            services.deliver_to_url(
                workspace=workspace,
                url="https://example.com/webhook-target",
                event_type="workflow.webhook",
                payload={},
                dedupe_key="run-1",
            )
        with django_capture_on_commit_callbacks(execute=True):
            second = services.deliver_to_url(
                workspace=workspace,
                url="https://example.com/webhook-target",
                event_type="workflow.webhook",
                payload={},
                dedupe_key="run-1",
            )

        assert second is None
