from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workflows import services
from apps.workflows.exceptions import InvalidGraphError
from apps.workflows.models import Workflow, WorkflowRun
from apps.workflows.providers import get_action_provider
from apps.workflows.selectors import (
    get_draft_version,
    get_workflow_runs,
    get_workspace_workflow,
    get_workspace_workflows,
)
from apps.workflows.serializers import (
    SaveDraftRequestSerializer,
    TestRunRequestSerializer,
    WorkflowCreateRequestSerializer,
    WorkflowDetailSerializer,
    WorkflowRunSerializer,
    WorkflowSerializer,
    WorkflowVersionSerializer,
)
from apps.workflows.services import EdgeSpec, NodeSpec
from apps.workspaces.models import Role, Workspace
from apps.workspaces.permissions import IsWorkspaceMember, get_workspace_membership

# Building/activating workflows is a manager-level action; any member
# can view them and run a test-run to check their own draft.
_CAN_EDIT_ROLES = {Role.OWNER, Role.ADMIN}


def _require_editor(request: Request) -> None:
    if get_workspace_membership(request).role not in _CAN_EDIT_ROLES:
        raise PermissionDenied("You do not have permission to edit workflows.")


class WorkflowListCreateView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses=WorkflowSerializer(many=True))
    def get(self, request: Request, workspace_id: str) -> Response:
        workflows = get_workspace_workflows(workspace_id=workspace_id)
        return Response(WorkflowSerializer(workflows, many=True).data)

    @extend_schema(request=WorkflowCreateRequestSerializer, responses=WorkflowDetailSerializer)
    def post(self, request: Request, workspace_id: str) -> Response:
        _require_editor(request)
        workspace = get_object_or_404(Workspace, id=workspace_id)
        payload = WorkflowCreateRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        workflow = services.create_workflow(
            workspace=workspace, user=request.user, name=payload.validated_data["name"]
        )
        return Response(WorkflowDetailSerializer(workflow).data, status=201)


class WorkflowDetailView(APIView):
    permission_classes = [IsWorkspaceMember]

    def _get_workflow(self, workspace_id: str, workflow_id: str) -> Workflow:
        workflow = get_workspace_workflow(workspace_id=workspace_id, workflow_id=workflow_id)
        if workflow is None:
            raise NotFound("Workflow not found.")
        return workflow

    @extend_schema(responses=WorkflowDetailSerializer)
    def get(self, request: Request, workspace_id: str, workflow_id: str) -> Response:
        workflow = self._get_workflow(workspace_id, workflow_id)
        return Response(WorkflowDetailSerializer(workflow).data)


class WorkflowDraftView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=SaveDraftRequestSerializer, responses=WorkflowVersionSerializer)
    def put(self, request: Request, workspace_id: str, workflow_id: str) -> Response:
        _require_editor(request)
        workflow = get_workspace_workflow(workspace_id=workspace_id, workflow_id=workflow_id)
        if workflow is None:
            raise NotFound("Workflow not found.")

        payload = SaveDraftRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        draft = services.get_or_create_draft_version(workflow=workflow, user=request.user)
        nodes = [NodeSpec(**n) for n in payload.validated_data["nodes"]]
        edges = [EdgeSpec(**e) for e in payload.validated_data["edges"]]
        errors = services.save_draft(version=draft, nodes=nodes, edges=edges)

        draft.refresh_from_db()
        data = WorkflowVersionSerializer(draft).data
        data["validation_errors"] = errors
        return Response(data)


class WorkflowActivateView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=None, responses=WorkflowVersionSerializer)
    def post(self, request: Request, workspace_id: str, workflow_id: str) -> Response:
        _require_editor(request)
        workflow = get_workspace_workflow(workspace_id=workspace_id, workflow_id=workflow_id)
        if workflow is None:
            raise NotFound("Workflow not found.")

        draft = get_draft_version(workflow=workflow)
        if draft is None:
            raise InvalidGraphError("There is no draft version to activate.")

        version = services.activate_version(version=draft, user=request.user)
        return Response(WorkflowVersionSerializer(version).data)


class WorkflowDeactivateView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=None, responses=WorkflowSerializer)
    def post(self, request: Request, workspace_id: str, workflow_id: str) -> Response:
        _require_editor(request)
        workflow = get_workspace_workflow(workspace_id=workspace_id, workflow_id=workflow_id)
        if workflow is None:
            raise NotFound("Workflow not found.")

        workflow = services.deactivate_workflow(workflow=workflow, user=request.user)
        return Response(WorkflowSerializer(workflow).data)


class WorkflowTestRunView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=TestRunRequestSerializer, responses=WorkflowRunSerializer)
    def post(self, request: Request, workspace_id: str, workflow_id: str) -> Response:
        workflow = get_workspace_workflow(workspace_id=workspace_id, workflow_id=workflow_id)
        if workflow is None:
            raise NotFound("Workflow not found.")

        version = get_draft_version(workflow=workflow) or workflow.active_version
        if version is None:
            raise InvalidGraphError("There is no version to test.")

        payload = TestRunRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        run = WorkflowRun.objects.create(
            workflow=workflow,
            version=version,
            workspace_id=workspace_id,
            trigger_context=payload.validated_data["trigger_context"],
            is_test_run=True,
        )
        run = services.execute_workflow(run=run, provider=get_action_provider())
        return Response(WorkflowRunSerializer(run).data, status=201)


class WorkflowRunListView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses=WorkflowRunSerializer(many=True))
    def get(self, request: Request, workspace_id: str, workflow_id: str) -> Response:
        workflow = get_workspace_workflow(workspace_id=workspace_id, workflow_id=workflow_id)
        if workflow is None:
            raise NotFound("Workflow not found.")
        runs = get_workflow_runs(workflow_id=workflow_id)
        return Response(WorkflowRunSerializer(runs, many=True).data)
