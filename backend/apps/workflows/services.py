"""Business logic for workflow graph validation, versioning/activation,
and deterministic execution — kept out of views/tasks per the project's
non-negotiable rule. Four entry points matter most:

- `save_draft` — replaces a draft version's nodes/edges wholesale.
- `activate_version` / `deactivate_workflow` — the immutability boundary.
- `trigger_workflows` — matches a real event to active workflows and
  enqueues idempotent runs.
- `execute_workflow` — walks the graph deterministically for one run.
"""

from dataclasses import dataclass, field
from functools import partial
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.workflows.exceptions import InvalidGraphError, VersionImmutableError
from apps.workflows.models import (
    ACTION_KINDS,
    CONDITION_KINDS,
    RETRYABLE_ACTION_KINDS,
    TRIGGER_KINDS,
    NodeType,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowStepRun,
    WorkflowStepRunStatus,
    WorkflowVersion,
    WorkflowVersionStatus,
)
from apps.workflows.providers import ActionProvider, ActionProviderError

MAX_ACTION_ATTEMPTS = 3


# --- Graph validation --------------------------------------------------


@dataclass(frozen=True)
class NodeSpec:
    node_key: str
    node_type: str
    kind: str
    config: dict
    position: dict = field(default_factory=dict)


@dataclass(frozen=True)
class EdgeSpec:
    source_node_key: str
    target_node_key: str
    branch: str = ""


def validate_graph(nodes: list[NodeSpec], edges: list[EdgeSpec]) -> list[str]:
    """Returns a list of human-readable validation messages — empty
    means the graph is valid. Never raises; callers decide whether an
    invalid graph is acceptable (a draft can be saved invalid; only
    activation enforces validity — see activate_version)."""
    errors: list[str] = []
    by_key = {n.node_key: n for n in nodes}

    if len(by_key) != len(nodes):
        errors.append("Node keys must be unique.")

    triggers = [n for n in nodes if n.node_type == NodeType.TRIGGER]
    if len(triggers) != 1:
        errors.append("A workflow must have exactly one trigger node.")

    for node in nodes:
        if node.node_type == NodeType.TRIGGER and node.kind not in TRIGGER_KINDS:
            errors.append(f"Unknown trigger kind: {node.kind}.")
        if node.node_type == NodeType.CONDITION and node.kind not in CONDITION_KINDS:
            errors.append(f"Unknown condition kind: {node.kind}.")
        if node.node_type == NodeType.ACTION and node.kind not in ACTION_KINDS:
            errors.append(f"Unknown action kind: {node.kind}.")
        errors.extend(_validate_node_config(node))

    for edge in edges:
        if edge.source_node_key not in by_key:
            errors.append(f"Edge references unknown source node: {edge.source_node_key}.")
        if edge.target_node_key not in by_key:
            errors.append(f"Edge references unknown target node: {edge.target_node_key}.")

    outgoing: dict[str, list[EdgeSpec]] = {}
    for edge in edges:
        outgoing.setdefault(edge.source_node_key, []).append(edge)

    for node in nodes:
        edges_out = outgoing.get(node.node_key, [])
        if node.node_type == NodeType.CONDITION:
            branches = sorted(e.branch for e in edges_out)
            if branches != ["false", "true"]:
                errors.append(
                    f"Condition node '{node.node_key}' needs exactly a true and a false branch."
                )
        else:
            if len(edges_out) > 1:
                errors.append(f"Node '{node.node_key}' can only have one outgoing path.")
            if edges_out and edges_out[0].branch:
                errors.append(f"Node '{node.node_key}' is not a condition and cannot branch.")

    if triggers and not errors:
        reachable = _reachable_nodes(triggers[0].node_key, outgoing)
        unreachable = set(by_key) - reachable
        if unreachable:
            errors.append(f"Unreachable node(s): {', '.join(sorted(unreachable))}.")
        if _has_cycle(triggers[0].node_key, outgoing):
            errors.append("Cycles are not supported.")

    return errors


def _validate_node_config(node: NodeSpec) -> list[str]:
    errors: list[str] = []
    config = node.config or {}
    if node.kind == "total_greater_than_threshold" and not isinstance(
        config.get("threshold"), (int, float)
    ):
        errors.append(f"Node '{node.node_key}' needs a numeric threshold.")
    if node.kind == "confidence_below_threshold" and not isinstance(
        config.get("threshold"), (int, float)
    ):
        errors.append(f"Node '{node.node_key}' needs a numeric threshold.")
    if node.kind == "add_tag" and not config.get("tag"):
        errors.append(f"Node '{node.node_key}' needs a tag value.")
    if node.kind == "trigger_webhook" and not config.get("url"):
        errors.append(f"Node '{node.node_key}' needs a webhook URL.")
    if node.kind == "send_notification" and not config.get("message"):
        errors.append(f"Node '{node.node_key}' needs a notification message.")
    return errors


def _reachable_nodes(start: str, outgoing: dict[str, list[EdgeSpec]]) -> set[str]:
    seen = {start}
    stack = [start]
    while stack:
        current = stack.pop()
        for edge in outgoing.get(current, []):
            if edge.target_node_key not in seen:
                seen.add(edge.target_node_key)
                stack.append(edge.target_node_key)
    return seen


def _has_cycle(start: str, outgoing: dict[str, list[EdgeSpec]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> bool:
        visiting.add(node)
        for edge in outgoing.get(node, []):
            target = edge.target_node_key
            if target in visiting:
                return True
            if target not in visited and dfs(target):
                return True
        visiting.discard(node)
        visited.add(node)
        return False

    return dfs(start)


# --- Versioning ----------------------------------------------------------


@transaction.atomic
def create_workflow(*, workspace, user, name: str) -> Workflow:
    workflow = Workflow.objects.create(workspace=workspace, name=name, created_by=user)
    get_or_create_draft_version(workflow=workflow, user=user)
    return workflow


@transaction.atomic
def get_or_create_draft_version(*, workflow: Workflow, user) -> WorkflowVersion:
    """Returns the existing draft if one exists; otherwise creates a new
    one, copied from the active version's graph if there is one (so
    editing an active workflow starts from its current shape rather
    than a blank canvas)."""
    draft = (
        workflow.versions.filter(status=WorkflowVersionStatus.DRAFT)
        .order_by("-version_number")
        .first()
    )
    if draft is not None:
        return draft

    last_version = workflow.versions.order_by("-version_number").first()
    next_number = (last_version.version_number + 1) if last_version else 1
    draft = WorkflowVersion.objects.create(
        workflow=workflow, version_number=next_number, created_by=user
    )

    active = workflow.active_version
    if active is not None:
        node_map = {}
        for node in active.nodes.all():
            new_node = WorkflowNode.objects.create(
                version=draft,
                node_key=node.node_key,
                node_type=node.node_type,
                kind=node.kind,
                config=node.config,
                position=node.position,
            )
            node_map[node.node_key] = new_node.node_key
        for edge in active.edges.all():
            WorkflowEdge.objects.create(
                version=draft,
                source_node_key=edge.source_node_key,
                target_node_key=edge.target_node_key,
                branch=edge.branch,
            )
    return draft


@transaction.atomic
def save_draft(
    *, version: WorkflowVersion, nodes: list[NodeSpec], edges: list[EdgeSpec]
) -> list[str]:
    """Replaces the draft's nodes/edges wholesale and returns current
    validation messages (empty means valid) — saving an invalid graph is
    allowed (it's a work in progress); only activate_version enforces
    validity."""
    if version.status != WorkflowVersionStatus.DRAFT:
        raise VersionImmutableError()

    version.nodes.all().delete()
    version.edges.all().delete()
    WorkflowNode.objects.bulk_create(
        [
            WorkflowNode(
                version=version,
                node_key=n.node_key,
                node_type=n.node_type,
                kind=n.kind,
                config=n.config,
                position=n.position,
            )
            for n in nodes
        ]
    )
    WorkflowEdge.objects.bulk_create(
        [
            WorkflowEdge(
                version=version,
                source_node_key=e.source_node_key,
                target_node_key=e.target_node_key,
                branch=e.branch,
            )
            for e in edges
        ]
    )
    return validate_graph(nodes, edges)


def _version_graph(version: WorkflowVersion) -> tuple[list[NodeSpec], list[EdgeSpec]]:
    nodes = [
        NodeSpec(
            node_key=n.node_key,
            node_type=n.node_type,
            kind=n.kind,
            config=n.config,
            position=n.position,
        )
        for n in version.nodes.all()
    ]
    edges = [
        EdgeSpec(
            source_node_key=e.source_node_key, target_node_key=e.target_node_key, branch=e.branch
        )
        for e in version.edges.all()
    ]
    return nodes, edges


@transaction.atomic
def activate_version(*, version: WorkflowVersion, user) -> WorkflowVersion:
    if version.status == WorkflowVersionStatus.ARCHIVED:
        raise VersionImmutableError()

    nodes, edges = _version_graph(version)
    errors = validate_graph(nodes, edges)
    if errors:
        raise InvalidGraphError("; ".join(errors))

    version.workflow.versions.filter(status=WorkflowVersionStatus.ACTIVE).update(
        status=WorkflowVersionStatus.ARCHIVED
    )
    version.status = WorkflowVersionStatus.ACTIVE
    version.activated_at = timezone.now()
    version.save(update_fields=["status", "activated_at"])

    version.workflow.is_active = True
    version.workflow.save(update_fields=["is_active"])

    record_event(
        event_type="workflow.activated",
        actor=user,
        workspace=version.workflow.workspace,
        metadata={"workflow_id": str(version.workflow_id), "version": version.version_number},
    )
    return version


@transaction.atomic
def deactivate_workflow(*, workflow: Workflow, user) -> Workflow:
    workflow.is_active = False
    workflow.save(update_fields=["is_active"])
    record_event(
        event_type="workflow.deactivated",
        actor=user,
        workspace=workflow.workspace,
        metadata={"workflow_id": str(workflow.id)},
    )
    return workflow


# --- Triggering and execution ---------------------------------------------


def dispatch_event(*, workspace_id: str, event: str, context: dict[str, Any]) -> list[WorkflowRun]:
    """The real integration point other apps call (see
    apps.documents.services.create_document and
    apps.extraction.services.transition_status) — creates idempotent
    runs via trigger_workflows and schedules each one, only after the
    current transaction commits (same on_commit pattern as
    apps.processing.services.enqueue_processing, for the same reason:
    a worker querying for the run before the row commits would 404)."""
    from apps.workflows.tasks import run_workflow

    def _schedule(run_id: str) -> None:
        run_workflow.delay(run_id)

    runs = trigger_workflows(workspace_id=workspace_id, event=event, context=context)
    for run in runs:
        transaction.on_commit(partial(_schedule, str(run.id)))
    return runs


def trigger_workflows(
    *, workspace_id: str, event: str, context: dict[str, Any]
) -> list[WorkflowRun]:
    """Matches `event` (e.g. "document_uploaded") against every active
    workflow in the workspace whose trigger node kind is that event,
    and creates one idempotent run each. Does not execute them — the
    caller schedules that (see apps.workflows.tasks), same request/
    response split as apps.processing's enqueue-then-run-later pattern."""
    runs: list[WorkflowRun] = []
    active_workflows = Workflow.objects.filter(workspace_id=workspace_id, is_active=True)
    for workflow in active_workflows:
        version = workflow.active_version
        if version is None:
            continue
        trigger_node = version.nodes.filter(node_type=NodeType.TRIGGER, kind=event).first()
        if trigger_node is None:
            continue

        document_id = context.get("document_id", "")
        idempotency_key = f"{version.id}:{event}:{document_id}"
        run, created = WorkflowRun.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={
                "workflow": workflow,
                "version": version,
                "workspace_id": workspace_id,
                "trigger_context": context,
            },
        )
        if created:
            runs.append(run)
    return runs


NodeHandler = Any  # callable(config: dict, context: dict, provider: ActionProvider) -> dict


def _handle_request_approval(config: dict, context: dict, provider: ActionProvider) -> dict:
    return {"approval_requested": True, "role": config.get("approver_role", "admin")}


def _handle_send_notification(config: dict, context: dict, provider: ActionProvider) -> dict:
    return provider.send_notification(
        message=config.get("message", ""), recipient=config.get("recipient", "workspace")
    )


def _handle_trigger_webhook(config: dict, context: dict, provider: ActionProvider) -> dict:
    return provider.trigger_webhook(
        url=config["url"], payload={"event": context.get("event"), **context}
    )


def _handle_add_tag(config: dict, context: dict, provider: ActionProvider) -> dict:
    return {"tag_added": config["tag"]}


def _handle_export_structured_data(config: dict, context: dict, provider: ActionProvider) -> dict:
    return {"exported": True, "format": config.get("format", "json")}


ACTION_HANDLERS: dict[str, NodeHandler] = {
    "request_approval": _handle_request_approval,
    "send_notification": _handle_send_notification,
    "trigger_webhook": _handle_trigger_webhook,
    "add_tag": _handle_add_tag,
    "export_structured_data": _handle_export_structured_data,
}


def _evaluate_condition(kind: str, config: dict, context: dict[str, Any]) -> bool:
    threshold = float(config.get("threshold") or 0)
    if kind == "total_greater_than_threshold":
        return float(context.get("total", 0)) > threshold
    if kind == "confidence_below_threshold":
        return float(context.get("confidence", 1)) < threshold
    return False


@transaction.atomic
def execute_workflow(*, run: WorkflowRun, provider: ActionProvider) -> WorkflowRun:
    """Deterministic: for the same graph and trigger_context, always
    produces the same sequence of step results. Runs are never re-
    executed by this function itself (see trigger_workflows'
    idempotency_key for duplicate-run prevention); calling it twice on
    the same run would append duplicate step rows, so callers must only
    call it once per run — apps.workflows.tasks enforces that by
    checking run.status first."""
    if run.status not in (WorkflowRunStatus.QUEUED,):
        return run

    run.status = WorkflowRunStatus.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at"])

    version = run.version
    nodes = {n.node_key: n for n in version.nodes.all()}
    outgoing: dict[str, list[WorkflowEdge]] = {}
    for edge in version.edges.all():
        outgoing.setdefault(edge.source_node_key, []).append(edge)

    trigger_node = next((n for n in nodes.values() if n.node_type == NodeType.TRIGGER), None)
    if trigger_node is None:
        run.status = WorkflowRunStatus.FAILED
        run.error_code = "no_trigger_node"
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "error_code", "completed_at"])
        return run

    current_key: str | None = trigger_node.node_key
    while current_key is not None:
        node = nodes[current_key]
        next_key: str | None = None

        if node.node_type == NodeType.TRIGGER:
            WorkflowStepRun.objects.create(
                run=run,
                node_key=node.node_key,
                node_kind=node.kind,
                status=WorkflowStepRunStatus.SUCCEEDED,
                completed_at=timezone.now(),
            )
            edges_out = outgoing.get(node.node_key, [])
            next_key = edges_out[0].target_node_key if edges_out else None

        elif node.node_type == NodeType.CONDITION:
            result = _evaluate_condition(node.kind, node.config, run.trigger_context)
            WorkflowStepRun.objects.create(
                run=run,
                node_key=node.node_key,
                node_kind=node.kind,
                status=WorkflowStepRunStatus.SUCCEEDED,
                output={"result": result},
                completed_at=timezone.now(),
            )
            branch = "true" if result else "false"
            branch_edge = next(
                (e for e in outgoing.get(node.node_key, []) if e.branch == branch), None
            )
            next_key = branch_edge.target_node_key if branch_edge else None

        else:  # ACTION
            handler = ACTION_HANDLERS[node.kind]
            retryable = node.kind in RETRYABLE_ACTION_KINDS
            attempts = 0
            output: dict = {}
            error_code = ""
            succeeded = False
            max_attempts = MAX_ACTION_ATTEMPTS if retryable else 1
            while attempts < max_attempts and not succeeded:
                attempts += 1
                try:
                    output = handler(node.config, run.trigger_context, provider)
                    succeeded = True
                except ActionProviderError:
                    error_code = "provider_unavailable"
                    if not retryable:
                        break
                    continue
                except KeyError:
                    error_code = "invalid_config"
                    break

            WorkflowStepRun.objects.create(
                run=run,
                node_key=node.node_key,
                node_kind=node.kind,
                status=(
                    WorkflowStepRunStatus.SUCCEEDED if succeeded else WorkflowStepRunStatus.FAILED
                ),
                output=output,
                error_code=error_code,
                attempt_count=attempts,
                completed_at=timezone.now(),
            )
            if not succeeded:
                run.status = WorkflowRunStatus.FAILED
                run.error_code = error_code
                run.completed_at = timezone.now()
                run.save(update_fields=["status", "error_code", "completed_at"])
                return run

            edges_out = outgoing.get(node.node_key, [])
            next_key = edges_out[0].target_node_key if edges_out else None

        current_key = next_key

    run.status = WorkflowRunStatus.COMPLETED
    run.completed_at = timezone.now()
    run.save(update_fields=["status", "completed_at"])
    return run
