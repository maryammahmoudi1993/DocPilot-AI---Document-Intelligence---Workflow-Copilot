from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.selectors import get_workspace_audit_events
from apps.audit.serializers import AuditEventSerializer
from apps.workspaces.permissions import IsWorkspaceMember


class AuditEventPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class AuditEventListView(APIView):
    """Read-only — see apps/audit/selectors.py's docstring on why an
    update/delete path deliberately does not exist anywhere in this
    app, which is what makes audit events immutable through the public
    API (project non-negotiable rule)."""

    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses=AuditEventSerializer(many=True))
    def get(self, request: Request, workspace_id: str) -> Response:
        since = parse_datetime(request.query_params.get("since", "") or "")
        until = parse_datetime(request.query_params.get("until", "") or "")
        events = get_workspace_audit_events(
            workspace_id=workspace_id,
            event_type=request.query_params.get("event_type") or None,
            since=since,
            until=until,
        )
        paginator = AuditEventPagination()
        page = paginator.paginate_queryset(events, request)
        return paginator.get_paginated_response(AuditEventSerializer(page, many=True).data)
