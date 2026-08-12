import pytest
from django.core.management import call_command

from apps.approvals.models import ApprovalRequest
from apps.audit.models import AuditEvent
from apps.documents.models import Document
from apps.notifications.models import Notification, WebhookEndpoint
from apps.workflows.models import Workflow
from apps.workspaces.models import Role, Workspace, WorkspaceMembership
from tests.factories import (
    ApprovalRequestFactory,
    DocumentFactory,
    NotificationFactory,
    WebhookEndpointFactory,
    WorkflowFactory,
)


@pytest.mark.django_db
def test_reset_demo_data_creates_the_base_seed_when_nothing_exists():
    call_command("reset_demo_data")

    workspace = Workspace.objects.get(slug="demo-workspace")
    assert WorkspaceMembership.objects.filter(workspace=workspace).count() == 5


@pytest.mark.django_db
def test_reset_demo_data_clears_workspace_scoped_content_but_keeps_users_and_membership():
    call_command("seed_demo_data")
    workspace = Workspace.objects.get(slug="demo-workspace")
    DocumentFactory(workspace=workspace)
    ApprovalRequestFactory(workspace=workspace)
    WorkflowFactory(workspace=workspace)
    NotificationFactory(workspace=workspace)
    WebhookEndpointFactory(workspace=workspace)
    from apps.audit.services import record_event

    record_event(event_type="document.uploaded", workspace=workspace)

    call_command("reset_demo_data")

    assert Document.objects.filter(workspace=workspace).count() == 0
    assert ApprovalRequest.objects.filter(workspace=workspace).count() == 0
    assert Workflow.objects.filter(workspace=workspace).count() == 0
    assert Notification.objects.filter(workspace=workspace).count() == 0
    assert WebhookEndpoint.objects.filter(workspace=workspace).count() == 0
    assert AuditEvent.objects.filter(workspace=workspace).count() == 0
    # The base seed (workspace, demo users, memberships) survives reset —
    # a demo reset should never lock the demo operator out.
    assert Workspace.objects.filter(slug="demo-workspace").count() == 1
    assert WorkspaceMembership.objects.filter(workspace=workspace, role=Role.OWNER).exists()


@pytest.mark.django_db
def test_reset_demo_data_does_not_touch_other_workspaces():
    from tests.factories import WorkspaceFactory

    other_workspace = WorkspaceFactory()
    DocumentFactory(workspace=other_workspace)

    call_command("reset_demo_data")

    assert Document.objects.filter(workspace=other_workspace).count() == 1


@pytest.mark.django_db
def test_reset_demo_data_is_idempotent():
    call_command("reset_demo_data")
    call_command("reset_demo_data")

    assert Workspace.objects.filter(slug="demo-workspace").count() == 1
