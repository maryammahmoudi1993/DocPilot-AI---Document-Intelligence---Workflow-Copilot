"""Versioned workflow graph and execution models.

A `Workflow` owns a sequence of `WorkflowVersion`s (like a document has
revisions); only one version is ever active at a time. An activated
version's nodes/edges become immutable (see services.activate_workflow)
— editing after that always means creating a new draft version first,
never mutating a version something may already be running against.
"""

import uuid

from django.conf import settings
from django.db import models


class WorkflowVersionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class NodeType(models.TextChoices):
    TRIGGER = "trigger", "Trigger"
    CONDITION = "condition", "Condition"
    ACTION = "action", "Action"


# Concrete node kinds this phase implements (see services.NODE_HANDLERS /
# providers.py for what each one actually does). `kind` is stored inside
# WorkflowNode.config (not a separate column) since it's freeform enough
# per NodeType that a single choices field covering all three types
# would need constant expansion; validated against this set instead —
# see services.validate_graph.
TRIGGER_KINDS = {"document_uploaded", "document_approved"}
CONDITION_KINDS = {"total_greater_than_threshold", "confidence_below_threshold"}
ACTION_KINDS = {
    "request_approval",
    "send_notification",
    "trigger_webhook",
    "add_tag",
    "export_structured_data",
}
# Actions whose failure is worth retrying (a transient network/provider
# issue) — everything else fails a step run immediately. Mirrors the
# retryable/non-retryable split apps.processing already established.
RETRYABLE_ACTION_KINDS = {"trigger_webhook", "send_notification"}


class Workflow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="workflows"
    )
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["workspace", "-updated_at"])]
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.name

    @property
    def active_version(self) -> "WorkflowVersion | None":
        return self.versions.filter(status=WorkflowVersionStatus.ACTIVE).first()


class WorkflowVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16, choices=WorkflowVersionStatus.choices, default=WorkflowVersionStatus.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["workflow", "-version_number"])]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "version_number"], name="unique_version_number_per_workflow"
            )
        ]
        ordering = ["-version_number"]

    def __str__(self) -> str:
        return f"WorkflowVersion({self.workflow_id}, v{self.version_number})"


class WorkflowNode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey(WorkflowVersion, on_delete=models.CASCADE, related_name="nodes")
    # Client-assigned stable id (e.g. "node-3") — what edges reference
    # and what the React Flow canvas already knows each node as, so the
    # frontend never has to re-map ids after a save.
    node_key = models.CharField(max_length=64)
    node_type = models.CharField(max_length=16, choices=NodeType.choices)
    kind = models.CharField(max_length=64)
    # e.g. {"threshold": 1000} for total_greater_than_threshold,
    # {"tag": "needs-review"} for add_tag, {"url": "..."} for
    # trigger_webhook. Shape depends on `kind` — validated in
    # services.validate_graph, not at the model layer.
    config = models.JSONField(default=dict, blank=True)
    position = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["version", "node_key"])]
        constraints = [
            models.UniqueConstraint(
                fields=["version", "node_key"], name="unique_node_key_per_version"
            )
        ]

    def __str__(self) -> str:
        return f"WorkflowNode({self.version_id}, {self.node_key})"


class WorkflowEdge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey(WorkflowVersion, on_delete=models.CASCADE, related_name="edges")
    source_node_key = models.CharField(max_length=64)
    target_node_key = models.CharField(max_length=64)
    # "true" / "false" for a condition node's two branches; blank for an
    # edge leaving a trigger or action node (exactly one outgoing edge).
    branch = models.CharField(max_length=8, blank=True)

    class Meta:
        indexes = [models.Index(fields=["version", "source_node_key"])]

    def __str__(self) -> str:
        return f"WorkflowEdge({self.source_node_key} -> {self.target_node_key})"


class WorkflowRunStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class WorkflowRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="runs")
    version = models.ForeignKey(WorkflowVersion, on_delete=models.CASCADE, related_name="runs")
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="workflow_runs"
    )
    status = models.CharField(
        max_length=16, choices=WorkflowRunStatus.choices, default=WorkflowRunStatus.QUEUED
    )
    # What triggered this run — e.g. {"event": "document_uploaded",
    # "document_id": "..."}. Read by condition nodes during execution.
    trigger_context = models.JSONField(default=dict, blank=True)
    # Deliberate real HTTP/test-run distinction: a test run never
    # actually calls a real action provider's side effect (see
    # services.execute_workflow's `is_test` flag) and is excluded from
    # the idempotency_key uniqueness a real trigger-fired run needs.
    is_test_run = models.BooleanField(default=False)
    # e.g. f"{version_id}:document_approved:{document_id}" — see
    # services.trigger_workflows. Null for test runs (never
    # deduplicated).
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001
    error_code = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["workflow", "-created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                name="unique_idempotency_key",
                condition=models.Q(idempotency_key__isnull=False),
            )
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"WorkflowRun({self.workflow_id}, {self.status})"


class WorkflowStepRunStatus(models.TextChoices):
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"


class WorkflowStepRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(WorkflowRun, on_delete=models.CASCADE, related_name="step_runs")
    node_key = models.CharField(max_length=64)
    node_kind = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=WorkflowStepRunStatus.choices)
    # Safe, bounded — a condition's evaluated result, an action's
    # deterministic mock output (e.g. {"tag_added": "needs-review"}).
    # Never raw document content.
    output = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["run", "started_at"])]
        ordering = ["started_at"]

    def __str__(self) -> str:
        return f"WorkflowStepRun({self.run_id}, {self.node_key})"
