import pytest

from apps.workflows import services
from apps.workflows.models import WorkflowRun, WorkflowRunStatus
from apps.workflows.services import EdgeSpec, NodeSpec
from apps.workflows.tasks import run_workflow
from tests.factories import WorkflowFactory


@pytest.mark.django_db
def test_a_missing_run_id_is_a_safe_no_op():
    run_workflow.delay("00000000-0000-0000-0000-000000000000")  # must not raise


@pytest.mark.django_db
def test_a_run_already_past_queued_is_a_safe_no_op():
    workflow = WorkflowFactory()
    draft = services.get_or_create_draft_version(workflow=workflow, user=None)
    services.save_draft(
        version=draft,
        nodes=[
            NodeSpec(node_key="t1", node_type="trigger", kind="document_uploaded", config={}),
            NodeSpec(node_key="a1", node_type="action", kind="add_tag", config={"tag": "x"}),
        ],
        edges=[EdgeSpec(source_node_key="t1", target_node_key="a1")],
    )
    version = services.activate_version(version=draft, user=None)
    run = WorkflowRun.objects.create(
        workflow=workflow,
        version=version,
        workspace=workflow.workspace,
        status=WorkflowRunStatus.COMPLETED,
    )

    run_workflow.delay(str(run.id))

    run.refresh_from_db()
    assert run.step_runs.count() == 0  # never executed a second time
