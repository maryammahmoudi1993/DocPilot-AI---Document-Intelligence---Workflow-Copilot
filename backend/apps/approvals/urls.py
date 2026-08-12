from django.urls import path

from apps.approvals.views import (
    ApprovalCommentListCreateView,
    ApprovalDecisionView,
    ApprovalDetailView,
    ApprovalListView,
)

urlpatterns = [
    path("", ApprovalListView.as_view(), name="approval-list"),
    path("<uuid:approval_id>/", ApprovalDetailView.as_view(), name="approval-detail"),
    path("<uuid:approval_id>/decide/", ApprovalDecisionView.as_view(), name="approval-decide"),
    path(
        "<uuid:approval_id>/comments/",
        ApprovalCommentListCreateView.as_view(),
        name="approval-comments",
    ),
]
