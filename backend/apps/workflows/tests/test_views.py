import pytest
from django.urls import reverse

from apps.workflows import services
from apps.workflows.services import EdgeSpec, NodeSpec
from apps.workspaces.models import Role
from tests.factories import (
    UserFactory,
    WorkflowFactory,
    WorkspaceFactory,
    WorkspaceMembershipFactory,
)


@pytest.fixture
def workspace():
    return WorkspaceFactory()


def _client_with_role(api_client, workspace, role=Role.VIEWER):
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace, role=role)
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.mark.django_db
class TestWorkflowListCreateView:
    def test_admin_can_create_a_workflow(self, api_client, workspace):
        _client_with_role(api_client, workspace, Role.ADMIN)

        response = api_client.post(
            reverse("workflow-list", args=[workspace.id]),
            {"name": "Invoice approval"},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["name"] == "Invoice approval"
        assert response.data["draft_version"] is not None

    def test_viewer_cannot_create_a_workflow(self, api_client, workspace):
        _client_with_role(api_client, workspace, Role.VIEWER)

        response = api_client.post(
            reverse("workflow-list", args=[workspace.id]),
            {"name": "Invoice approval"},
            format="json",
        )

        assert response.status_code == 403

    def test_lists_only_this_workspaces_workflows(self, api_client, workspace):
        WorkflowFactory(workspace=workspace)
        WorkflowFactory()  # another workspace
        _client_with_role(api_client, workspace)

        response = api_client.get(reverse("workflow-list", args=[workspace.id]))

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_anonymous_is_rejected(self, api_client, workspace):
        response = api_client.get(reverse("workflow-list", args=[workspace.id]))

        assert response.status_code == 401


@pytest.mark.django_db
class TestWorkflowDraftAndActivate:
    def _draft_payload(self):
        return {
            "nodes": [
                {
                    "node_key": "t1",
                    "node_type": "trigger",
                    "kind": "document_uploaded",
                    "config": {},
                },
                {
                    "node_key": "a1",
                    "node_type": "action",
                    "kind": "add_tag",
                    "config": {"tag": "x"},
                },
            ],
            "edges": [{"source_node_key": "t1", "target_node_key": "a1", "branch": ""}],
        }

    def test_saving_an_invalid_draft_returns_validation_errors_but_still_saves(
        self, api_client, workspace
    ):
        workflow = WorkflowFactory(workspace=workspace)
        _client_with_role(api_client, workspace, Role.ADMIN)

        response = api_client.put(
            reverse("workflow-draft", args=[workspace.id, workflow.id]),
            {
                "nodes": [
                    {
                        "node_key": "a1",
                        "node_type": "action",
                        "kind": "add_tag",
                        "config": {"tag": "x"},
                    }
                ],
                "edges": [],
            },
            format="json",
        )

        assert response.status_code == 200
        assert len(response.data["validation_errors"]) > 0
        assert len(response.data["nodes"]) == 1

    def test_activating_an_invalid_graph_returns_a_stable_error_code(self, api_client, workspace):
        workflow = WorkflowFactory(workspace=workspace)
        _client_with_role(api_client, workspace, Role.ADMIN)
        api_client.put(
            reverse("workflow-draft", args=[workspace.id, workflow.id]),
            {"nodes": [], "edges": []},
            format="json",
        )

        response = api_client.post(reverse("workflow-activate", args=[workspace.id, workflow.id]))

        assert response.status_code == 400
        assert response.data["error"]["code"] == "invalid_graph"

    def test_saving_and_activating_a_valid_draft_succeeds(self, api_client, workspace):
        workflow = WorkflowFactory(workspace=workspace)
        _client_with_role(api_client, workspace, Role.ADMIN)
        api_client.put(
            reverse("workflow-draft", args=[workspace.id, workflow.id]),
            self._draft_payload(),
            format="json",
        )

        response = api_client.post(reverse("workflow-activate", args=[workspace.id, workflow.id]))

        assert response.status_code == 200
        assert response.data["status"] == "active"

    def test_deactivating_a_workflow(self, api_client, workspace):
        workflow = WorkflowFactory(workspace=workspace)
        _client_with_role(api_client, workspace, Role.ADMIN)
        api_client.put(
            reverse("workflow-draft", args=[workspace.id, workflow.id]),
            self._draft_payload(),
            format="json",
        )
        api_client.post(reverse("workflow-activate", args=[workspace.id, workflow.id]))

        response = api_client.post(reverse("workflow-deactivate", args=[workspace.id, workflow.id]))

        assert response.status_code == 200
        assert response.data["is_active"] is False


@pytest.mark.django_db
class TestWorkflowTestRun:
    def test_a_member_can_test_run_a_draft(self, api_client, workspace):
        workflow = WorkflowFactory(workspace=workspace)
        draft = services.get_or_create_draft_version(workflow=workflow, user=None)
        services.save_draft(
            version=draft,
            nodes=[
                NodeSpec(node_key="t1", node_type="trigger", kind="document_uploaded", config={}),
                NodeSpec(node_key="a1", node_type="action", kind="add_tag", config={"tag": "x"}),
            ],
            edges=[EdgeSpec(source_node_key="t1", target_node_key="a1")],
        )
        _client_with_role(api_client, workspace, Role.VIEWER)

        response = api_client.post(
            reverse("workflow-test-run", args=[workspace.id, workflow.id]),
            {"trigger_context": {}},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["is_test_run"] is True
        assert response.data["status"] == "completed"


@pytest.mark.django_db
class TestWorkflowRunListView:
    def test_workspace_isolation(self, api_client, workspace):
        other_workflow = WorkflowFactory()
        _client_with_role(api_client, workspace)

        response = api_client.get(
            reverse("workflow-run-list", args=[workspace.id, other_workflow.id])
        )

        assert response.status_code == 404
