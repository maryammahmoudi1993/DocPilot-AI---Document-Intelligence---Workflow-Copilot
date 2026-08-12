import pytest

from apps.workflows import services
from apps.workflows.exceptions import InvalidGraphError, VersionImmutableError
from apps.workflows.models import (
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowStepRunStatus,
    WorkflowVersionStatus,
)
from apps.workflows.providers import ActionProviderError
from apps.workflows.services import EdgeSpec, NodeSpec
from tests.factories import WorkflowFactory, WorkspaceFactory


def _trigger(key="t1", kind="document_uploaded"):
    return NodeSpec(node_key=key, node_type="trigger", kind=kind, config={})


def _condition(key="c1", kind="total_greater_than_threshold", threshold=1000):
    return NodeSpec(node_key=key, node_type="condition", kind=kind, config={"threshold": threshold})


def _action(key="a1", kind="add_tag", config=None):
    return NodeSpec(
        node_key=key, node_type="action", kind=kind, config=config or {"tag": "flagged"}
    )


class FakeActionProvider:
    def __init__(self, fail_times=0):
        self.fail_times = fail_times
        self.calls = 0

    def send_notification(self, *, message, recipient):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ActionProviderError("timeout")
        return {"delivered": True}

    def trigger_webhook(self, *, url, payload):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ActionProviderError("timeout")
        return {"delivered": True}


@pytest.mark.django_db
class TestValidateGraph:
    def test_a_valid_linear_graph_has_no_errors(self):
        nodes = [_trigger(), _action()]
        edges = [EdgeSpec(source_node_key="t1", target_node_key="a1")]

        assert services.validate_graph(nodes, edges) == []

    def test_missing_trigger_is_rejected(self):
        nodes = [_action()]

        errors = services.validate_graph(nodes, [])

        assert any("trigger" in e.lower() for e in errors)

    def test_more_than_one_trigger_is_rejected(self):
        nodes = [_trigger("t1"), _trigger("t2"), _action()]
        edges = [EdgeSpec(source_node_key="t1", target_node_key="a1")]

        errors = services.validate_graph(nodes, edges)

        assert any("exactly one trigger" in e for e in errors)

    def test_a_cycle_is_rejected(self):
        nodes = [_trigger(), _action("a1"), _action("a2")]
        edges = [
            EdgeSpec(source_node_key="t1", target_node_key="a1"),
            EdgeSpec(source_node_key="a1", target_node_key="a2"),
            EdgeSpec(source_node_key="a2", target_node_key="a1"),
        ]

        errors = services.validate_graph(nodes, edges)

        assert any("cycle" in e.lower() for e in errors)

    def test_condition_branching_requires_both_branches(self):
        nodes = [_trigger(), _condition(), _action()]
        edges = [
            EdgeSpec(source_node_key="t1", target_node_key="c1"),
            EdgeSpec(source_node_key="c1", target_node_key="a1", branch="true"),
        ]

        errors = services.validate_graph(nodes, edges)

        assert any("true and a false branch" in e for e in errors)

    def test_a_valid_condition_branch_graph_has_no_errors(self):
        nodes = [_trigger(), _condition(), _action("a1"), _action("a2")]
        edges = [
            EdgeSpec(source_node_key="t1", target_node_key="c1"),
            EdgeSpec(source_node_key="c1", target_node_key="a1", branch="true"),
            EdgeSpec(source_node_key="c1", target_node_key="a2", branch="false"),
        ]

        assert services.validate_graph(nodes, edges) == []

    def test_unreachable_node_is_rejected(self):
        nodes = [_trigger(), _action("a1"), _action("a2")]
        edges = [EdgeSpec(source_node_key="t1", target_node_key="a1")]

        errors = services.validate_graph(nodes, edges)

        assert any("unreachable" in e.lower() for e in errors)

    def test_missing_threshold_config_is_rejected(self):
        nodes = [
            _trigger(),
            NodeSpec(
                node_key="c1", node_type="condition", kind="total_greater_than_threshold", config={}
            ),
        ]
        edges = [EdgeSpec(source_node_key="t1", target_node_key="c1", branch="")]

        errors = services.validate_graph(nodes, edges)

        assert any("threshold" in e.lower() for e in errors)


@pytest.mark.django_db
class TestActivation:
    def test_cannot_activate_an_invalid_graph(self):
        workflow = WorkflowFactory()
        draft = services.get_or_create_draft_version(workflow=workflow, user=None)
        services.save_draft(version=draft, nodes=[_action()], edges=[])  # no trigger

        with pytest.raises(InvalidGraphError):
            services.activate_version(version=draft, user=None)

    def test_activating_a_valid_graph_marks_it_active_and_immutable(self):
        workflow = WorkflowFactory()
        draft = services.get_or_create_draft_version(workflow=workflow, user=None)
        services.save_draft(
            version=draft,
            nodes=[_trigger(), _action()],
            edges=[EdgeSpec(source_node_key="t1", target_node_key="a1")],
        )

        activated = services.activate_version(version=draft, user=None)

        assert activated.status == WorkflowVersionStatus.ACTIVE
        activated.workflow.refresh_from_db()
        assert activated.workflow.is_active is True

        with pytest.raises(VersionImmutableError):
            services.save_draft(version=activated, nodes=[], edges=[])

    def test_editing_an_active_workflow_creates_a_new_draft_without_touching_the_active_version(
        self,
    ):
        workflow = WorkflowFactory()
        draft = services.get_or_create_draft_version(workflow=workflow, user=None)
        services.save_draft(
            version=draft,
            nodes=[_trigger(), _action()],
            edges=[EdgeSpec(source_node_key="t1", target_node_key="a1")],
        )
        active = services.activate_version(version=draft, user=None)

        new_draft = services.get_or_create_draft_version(workflow=workflow, user=None)

        assert new_draft.id != active.id
        assert new_draft.status == WorkflowVersionStatus.DRAFT
        assert new_draft.version_number == active.version_number + 1
        # Copied from the active graph.
        assert set(new_draft.nodes.values_list("node_key", flat=True)) == {"t1", "a1"}


@pytest.mark.django_db
class TestExecuteWorkflow:
    def _active_run(self, *, nodes, edges, context=None):
        workflow = WorkflowFactory()
        draft = services.get_or_create_draft_version(workflow=workflow, user=None)
        services.save_draft(version=draft, nodes=nodes, edges=edges)
        version = services.activate_version(version=draft, user=None)
        return WorkflowRun.objects.create(
            workflow=workflow,
            version=version,
            workspace=workflow.workspace,
            trigger_context=context or {},
        )

    def test_condition_true_branch_is_taken(self):
        run = self._active_run(
            nodes=[_trigger(), _condition(threshold=100), _action("a1"), _action("a2")],
            edges=[
                EdgeSpec(source_node_key="t1", target_node_key="c1"),
                EdgeSpec(source_node_key="c1", target_node_key="a1", branch="true"),
                EdgeSpec(source_node_key="c1", target_node_key="a2", branch="false"),
            ],
            context={"total": 500},
        )

        result = services.execute_workflow(run=run, provider=FakeActionProvider())

        assert result.status == WorkflowRunStatus.COMPLETED
        step_keys = list(result.step_runs.values_list("node_key", flat=True))
        assert "a1" in step_keys
        assert "a2" not in step_keys

    def test_condition_false_branch_is_taken(self):
        run = self._active_run(
            nodes=[_trigger(), _condition(threshold=1000), _action("a1"), _action("a2")],
            edges=[
                EdgeSpec(source_node_key="t1", target_node_key="c1"),
                EdgeSpec(source_node_key="c1", target_node_key="a1", branch="true"),
                EdgeSpec(source_node_key="c1", target_node_key="a2", branch="false"),
            ],
            context={"total": 50},
        )

        result = services.execute_workflow(run=run, provider=FakeActionProvider())

        step_keys = list(result.step_runs.values_list("node_key", flat=True))
        assert "a2" in step_keys
        assert "a1" not in step_keys

    def test_a_failed_action_is_recorded_and_stops_the_run(self):
        run = self._active_run(
            nodes=[_trigger(), _action("a1", kind="add_tag", config={"tag": "x"}), _action("a2")],
            edges=[
                EdgeSpec(source_node_key="t1", target_node_key="a1"),
                EdgeSpec(source_node_key="a1", target_node_key="a2"),
            ],
        )
        # add_tag isn't retryable; force it to fail via a broken config
        # caught as invalid_config (KeyError path) by clearing the tag.
        node = run.version.nodes.get(node_key="a1")
        node.config = {}
        node.save()

        result = services.execute_workflow(run=run, provider=FakeActionProvider())

        assert result.status == WorkflowRunStatus.FAILED
        failed_step = result.step_runs.get(node_key="a1")
        assert failed_step.status == WorkflowStepRunStatus.FAILED
        assert not result.step_runs.filter(node_key="a2").exists()

    def test_retries_apply_only_to_retryable_actions(self):
        run = self._active_run(
            nodes=[_trigger(), _action("a1", kind="send_notification", config={"message": "hi"})],
            edges=[EdgeSpec(source_node_key="t1", target_node_key="a1")],
        )
        provider = FakeActionProvider(fail_times=2)

        result = services.execute_workflow(run=run, provider=provider)

        assert result.status == WorkflowRunStatus.COMPLETED
        step = result.step_runs.get(node_key="a1")
        assert step.attempt_count == 3

    def test_a_non_retryable_action_does_not_retry(self):
        run = self._active_run(
            nodes=[_trigger(), _action("a1", kind="add_tag", config={"tag": "x"})],
            edges=[EdgeSpec(source_node_key="t1", target_node_key="a1")],
        )
        provider = FakeActionProvider(fail_times=99)  # would always fail if called

        result = services.execute_workflow(run=run, provider=provider)

        # add_tag never calls the provider at all — succeeds regardless.
        assert result.status == WorkflowRunStatus.COMPLETED
        assert provider.calls == 0

    def test_execution_is_deterministic_for_the_same_input(self):
        workflow = WorkflowFactory()
        draft = services.get_or_create_draft_version(workflow=workflow, user=None)
        services.save_draft(
            version=draft,
            nodes=[_trigger(), _condition(threshold=100), _action("a1"), _action("a2")],
            edges=[
                EdgeSpec(source_node_key="t1", target_node_key="c1"),
                EdgeSpec(source_node_key="c1", target_node_key="a1", branch="true"),
                EdgeSpec(source_node_key="c1", target_node_key="a2", branch="false"),
            ],
        )
        version = services.activate_version(version=draft, user=None)

        run_a = WorkflowRun.objects.create(
            workflow=workflow,
            version=version,
            workspace=workflow.workspace,
            trigger_context={"total": 500},
        )
        run_b = WorkflowRun.objects.create(
            workflow=workflow,
            version=version,
            workspace=workflow.workspace,
            trigger_context={"total": 500},
        )
        services.execute_workflow(run=run_a, provider=FakeActionProvider())
        services.execute_workflow(run=run_b, provider=FakeActionProvider())

        keys_a = list(run_a.step_runs.values_list("node_key", "status"))
        keys_b = list(run_b.step_runs.values_list("node_key", "status"))
        assert keys_a == keys_b

    def test_calling_execute_twice_on_the_same_run_does_not_duplicate_steps(self):
        run = self._active_run(
            nodes=[_trigger(), _action("a1")],
            edges=[EdgeSpec(source_node_key="t1", target_node_key="a1")],
        )

        services.execute_workflow(run=run, provider=FakeActionProvider())
        run.refresh_from_db()
        first_count = run.step_runs.count()
        services.execute_workflow(run=run, provider=FakeActionProvider())

        assert run.step_runs.count() == first_count


@pytest.mark.django_db
class TestTriggerWorkflows:
    def test_duplicate_trigger_events_do_not_create_two_runs(self):
        workflow = WorkflowFactory()
        draft = services.get_or_create_draft_version(workflow=workflow, user=None)
        services.save_draft(
            version=draft,
            nodes=[_trigger(kind="document_approved"), _action()],
            edges=[EdgeSpec(source_node_key="t1", target_node_key="a1")],
        )
        services.activate_version(version=draft, user=None)

        context = {"document_id": "doc-1"}
        first = services.trigger_workflows(
            workspace_id=str(workflow.workspace_id), event="document_approved", context=context
        )
        second = services.trigger_workflows(
            workspace_id=str(workflow.workspace_id), event="document_approved", context=context
        )

        assert len(first) == 1
        assert len(second) == 0  # already exists — no duplicate

    def test_workflows_in_another_workspace_are_never_triggered(self):
        other_workspace = WorkspaceFactory()
        workflow = WorkflowFactory()  # different workspace
        draft = services.get_or_create_draft_version(workflow=workflow, user=None)
        services.save_draft(
            version=draft,
            nodes=[_trigger(kind="document_approved"), _action()],
            edges=[EdgeSpec(source_node_key="t1", target_node_key="a1")],
        )
        services.activate_version(version=draft, user=None)

        runs = services.trigger_workflows(
            workspace_id=str(other_workspace.id), event="document_approved", context={}
        )

        assert runs == []

    def test_an_inactive_workflow_is_not_triggered(self):
        workflow = WorkflowFactory()
        draft = services.get_or_create_draft_version(workflow=workflow, user=None)
        services.save_draft(
            version=draft,
            nodes=[_trigger(kind="document_approved"), _action()],
            edges=[EdgeSpec(source_node_key="t1", target_node_key="a1")],
        )
        services.activate_version(version=draft, user=None)
        services.deactivate_workflow(workflow=workflow, user=None)

        runs = services.trigger_workflows(
            workspace_id=str(workflow.workspace_id), event="document_approved", context={}
        )

        assert runs == []
