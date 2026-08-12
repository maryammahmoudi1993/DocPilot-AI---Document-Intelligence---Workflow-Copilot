from datetime import date

from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics import selectors
from apps.analytics.serializers import AnalyticsOverviewSerializer, DashboardSummarySerializer
from apps.workspaces.permissions import IsWorkspaceMember


class DashboardSummaryView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses={200: DashboardSummarySerializer})
    def get(self, request: Request, workspace_id) -> Response:
        summary = selectors.dashboard_summary(workspace_id=workspace_id)
        return Response(DashboardSummarySerializer(summary).data)


def _parse_range(request: Request) -> tuple[date, date]:
    since_param = request.query_params.get("since")
    until_param = request.query_params.get("until")
    if not since_param and not until_param:
        return selectors.default_date_range()

    since = parse_date(since_param) if since_param else None
    until = parse_date(until_param) if until_param else None
    if since is None or until is None:
        raise ValidationError({"since": "Provide both since and until as YYYY-MM-DD."})
    if since > until:
        raise ValidationError({"since": "since must not be after until."})
    return since, until


class AnalyticsOverviewView(APIView):
    """One response covering every Analytics-page chart — see
    AnalyticsOverviewSerializer's docstring for why this isn't six
    endpoints. `since`/`until` (YYYY-MM-DD) default to the trailing
    30 days when omitted."""

    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses={200: AnalyticsOverviewSerializer})
    def get(self, request: Request, workspace_id) -> Response:
        since, until = _parse_range(request)

        approval_duration_seconds = selectors.average_approval_duration_seconds(
            workspace_id=workspace_id
        )

        payload = {
            "since": since.isoformat(),
            "until": until.isoformat(),
            "processing_trends": selectors.processing_trends(
                workspace_id=workspace_id, since=since, until=until
            ),
            "document_type_counts": selectors.document_type_counts(workspace_id=workspace_id),
            "extraction_accuracy": selectors.extraction_accuracy_metrics(workspace_id=workspace_id),
            "review_rate": selectors.review_rate_metrics(workspace_id=workspace_id),
            "workflow_success": selectors.workflow_success_metrics(workspace_id=workspace_id),
            "approval_duration": {"average_duration_seconds": approval_duration_seconds},
        }
        return Response(AnalyticsOverviewSerializer(payload).data)
