import pytest

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from tests.factories import UserFactory, WorkspaceFactory


@pytest.mark.django_db
def test_record_event_persists_actor_workspace_and_metadata():
    user = UserFactory()
    workspace = WorkspaceFactory()

    event = record_event(
        event_type="workspace.member_added",
        actor=user,
        workspace=workspace,
        metadata={"role": "viewer"},
    )

    stored = AuditEvent.objects.get(id=event.id)
    assert stored.event_type == "workspace.member_added"
    assert stored.actor == user
    assert stored.workspace == workspace
    assert stored.metadata == {"role": "viewer"}


@pytest.mark.django_db
def test_record_event_defaults_to_empty_metadata_and_no_actor():
    event = record_event(event_type="auth.login_failed")

    assert event.actor is None
    assert event.workspace is None
    assert event.metadata == {}
