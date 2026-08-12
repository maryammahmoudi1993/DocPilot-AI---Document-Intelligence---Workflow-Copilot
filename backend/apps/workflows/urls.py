from django.urls import path

from apps.workflows.views import (
    WorkflowActivateView,
    WorkflowDeactivateView,
    WorkflowDetailView,
    WorkflowDraftView,
    WorkflowListCreateView,
    WorkflowRunListView,
    WorkflowTestRunView,
)

urlpatterns = [
    path("", WorkflowListCreateView.as_view(), name="workflow-list"),
    path("<uuid:workflow_id>/", WorkflowDetailView.as_view(), name="workflow-detail"),
    path("<uuid:workflow_id>/draft/", WorkflowDraftView.as_view(), name="workflow-draft"),
    path("<uuid:workflow_id>/activate/", WorkflowActivateView.as_view(), name="workflow-activate"),
    path(
        "<uuid:workflow_id>/deactivate/",
        WorkflowDeactivateView.as_view(),
        name="workflow-deactivate",
    ),
    path("<uuid:workflow_id>/test-run/", WorkflowTestRunView.as_view(), name="workflow-test-run"),
    path("<uuid:workflow_id>/runs/", WorkflowRunListView.as_view(), name="workflow-run-list"),
]
