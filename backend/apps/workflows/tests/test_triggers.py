"""Integration tests for the real trigger hooks — document upload and
extraction approval — wired into apps.documents/apps.extraction. Uses
CELERY_TASK_ALWAYS_EAGER (test settings) so the scheduled run executes
synchronously within the test, same pattern as apps.processing's tests.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents import services as document_services
from apps.extraction import services as extraction_services
from apps.extraction.models import ExtractionStatus
from apps.workflows import services as workflow_services
from apps.workflows.models import WorkflowRun, WorkflowRunStatus
from apps.workflows.services import EdgeSpec, NodeSpec
from tests.factories import (
    DocumentExtractionFactory,
    DocumentFactory,
    ExtractedFieldFactory,
    UserFactory,
    WorkflowFactory,
    WorkspaceFactory,
)


def _activate_trigger_only_workflow(workspace, *, trigger_kind: str):
    workflow = WorkflowFactory(workspace=workspace)
    draft = workflow_services.get_or_create_draft_version(workflow=workflow, user=None)  # type: ignore[arg-type]
    workflow_services.save_draft(
        version=draft,
        nodes=[
            NodeSpec(node_key="t1", node_type="trigger", kind=trigger_kind, config={}),
            NodeSpec(node_key="a1", node_type="action", kind="add_tag", config={"tag": "auto"}),
        ],
        edges=[EdgeSpec(source_node_key="t1", target_node_key="a1")],
    )
    workflow_services.activate_version(version=draft, user=None)
    return workflow


@pytest.mark.django_db
def test_uploading_a_document_triggers_an_active_document_uploaded_workflow(
    fake_storage, django_capture_on_commit_callbacks
):
    workspace = WorkspaceFactory()
    _activate_trigger_only_workflow(workspace, trigger_kind="document_uploaded")
    user = UserFactory()
    file = SimpleUploadedFile("a.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf")

    with django_capture_on_commit_callbacks(execute=True):
        document = document_services.create_document(
            workspace=workspace, uploaded_by=user, uploaded_file=file, storage=fake_storage
        )

    run = WorkflowRun.objects.get(trigger_context__document_id=str(document.id))
    assert run.status == WorkflowRunStatus.COMPLETED


@pytest.mark.django_db
def test_approving_an_extraction_triggers_an_active_document_approved_workflow(
    django_capture_on_commit_callbacks,
):
    workspace = WorkspaceFactory()
    _activate_trigger_only_workflow(workspace, trigger_kind="document_approved")
    document = DocumentFactory(workspace=workspace)
    extraction = DocumentExtractionFactory(document=document, workspace=workspace)
    ExtractedFieldFactory(extraction=extraction, key="total", normalized_value="500.00")
    user = UserFactory()

    with django_capture_on_commit_callbacks(execute=True):
        extraction_services.transition_status(
            extraction=extraction,
            new_status=ExtractionStatus.APPROVED,
            user=user,
            expected_version=1,
        )

    run = WorkflowRun.objects.get(trigger_context__document_id=str(document.id))
    assert run.status == WorkflowRunStatus.COMPLETED
    assert run.trigger_context["total"] == 500.0


@pytest.mark.django_db
def test_a_workflow_dispatch_failure_does_not_block_document_upload(fake_storage, monkeypatch):
    workspace = WorkspaceFactory()
    user = UserFactory()
    file = SimpleUploadedFile("a.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf")

    def _boom(*args, **kwargs):
        raise RuntimeError("workflow engine exploded")

    monkeypatch.setattr("apps.workflows.services.dispatch_event", _boom)

    document = document_services.create_document(
        workspace=workspace, uploaded_by=user, uploaded_file=file, storage=fake_storage
    )

    assert document.id is not None  # upload still succeeded
