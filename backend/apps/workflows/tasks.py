"""Celery entry point for executing a queued WorkflowRun — mirrors
apps.processing.tasks' orchestrator shape (idempotent, safe no-op for a
missing or already-terminal run)."""

import logging

from celery import shared_task

from apps.workflows.models import WorkflowRun, WorkflowRunStatus
from apps.workflows.providers import get_action_provider
from apps.workflows.services import execute_workflow

logger = logging.getLogger(__name__)


@shared_task
def run_workflow(run_id: str) -> None:
    try:
        run = WorkflowRun.objects.select_related("version", "workflow").get(id=run_id)
    except WorkflowRun.DoesNotExist:
        logger.warning("workflow_run_not_found", extra={"run_id": run_id})
        return

    if run.status != WorkflowRunStatus.QUEUED:
        # Already running/terminal — a duplicate .delay() call (Celery's
        # at-least-once delivery redelivering the same task) is a safe
        # no-op, same idempotency guarantee as apps.processing.tasks.
        return

    execute_workflow(run=run, provider=get_action_provider())
