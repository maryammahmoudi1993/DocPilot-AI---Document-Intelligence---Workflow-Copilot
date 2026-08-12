from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.extraction.views import ExtractionQueueView
from apps.notifications.urls import integration_urlpatterns, notification_urlpatterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.health.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/workspaces/", include("apps.workspaces.urls")),
    path("api/workspaces/<uuid:workspace_id>/documents/", include("apps.documents.urls")),
    path(
        "api/workspaces/<uuid:workspace_id>/extractions/",
        ExtractionQueueView.as_view(),
        name="extraction-queue",
    ),
    path(
        "api/workspaces/<uuid:workspace_id>/assistant/conversations/",
        include("apps.assistant.urls"),
    ),
    path(
        "api/workspaces/<uuid:workspace_id>/workflows/",
        include("apps.workflows.urls"),
    ),
    path(
        "api/workspaces/<uuid:workspace_id>/approvals/",
        include("apps.approvals.urls"),
    ),
    path(
        "api/workspaces/<uuid:workspace_id>/notifications/",
        include((notification_urlpatterns, "notifications")),
    ),
    path(
        "api/workspaces/<uuid:workspace_id>/integrations/webhooks/",
        include((integration_urlpatterns, "integrations")),
    ),
    path(
        "api/workspaces/<uuid:workspace_id>/audit-events/",
        include("apps.audit.urls"),
    ),
    path(
        "api/workspaces/<uuid:workspace_id>/",
        include("apps.analytics.urls"),
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="schema-docs",
    ),
]
