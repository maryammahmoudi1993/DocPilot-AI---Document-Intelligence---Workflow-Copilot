from django.urls import path

from apps.workspaces.views import (
    MembershipDetailView,
    MembershipListCreateView,
    TransferOwnershipView,
    WorkspaceListView,
)

urlpatterns = [
    path("", WorkspaceListView.as_view(), name="workspace-list"),
    path(
        "<uuid:workspace_id>/members/", MembershipListCreateView.as_view(), name="workspace-members"
    ),
    path(
        "<uuid:workspace_id>/members/<uuid:membership_id>/",
        MembershipDetailView.as_view(),
        name="workspace-member-detail",
    ),
    path(
        "<uuid:workspace_id>/transfer-ownership/",
        TransferOwnershipView.as_view(),
        name="workspace-transfer-ownership",
    ),
]
