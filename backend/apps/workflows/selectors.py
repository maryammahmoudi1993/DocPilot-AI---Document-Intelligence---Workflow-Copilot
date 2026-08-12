from django.db.models import QuerySet

from apps.workflows.models import Workflow, WorkflowRun, WorkflowVersion


def get_workspace_workflows(*, workspace_id: str) -> QuerySet[Workflow]:
    return Workflow.objects.filter(workspace_id=workspace_id).order_by("-updated_at")


def get_workspace_workflow(*, workspace_id: str, workflow_id: str) -> Workflow | None:
    return Workflow.objects.filter(workspace_id=workspace_id, id=workflow_id).first()


def get_draft_version(*, workflow: Workflow) -> WorkflowVersion | None:
    from apps.workflows.models import WorkflowVersionStatus

    return (
        workflow.versions.filter(status=WorkflowVersionStatus.DRAFT)
        .order_by("-version_number")
        .first()
    )


def get_version_with_graph(*, version_id: str) -> WorkflowVersion | None:
    return WorkflowVersion.objects.filter(id=version_id).prefetch_related("nodes", "edges").first()


def get_workflow_runs(*, workflow_id: str) -> QuerySet[WorkflowRun]:
    return WorkflowRun.objects.filter(workflow_id=workflow_id).prefetch_related("step_runs")
