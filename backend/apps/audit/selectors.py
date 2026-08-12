from django.db.models import QuerySet

from apps.audit.models import AuditEvent


def get_workspace_audit_events(
    *, workspace_id: str, event_type: str | None = None, since=None, until=None
) -> QuerySet[AuditEvent]:
    """Read-only by construction: nothing in this module (or anywhere
    else in the codebase) exposes an update/delete path for AuditEvent
    — see apps/audit/views.py, which only ever wires a GET."""
    queryset = AuditEvent.objects.filter(workspace_id=workspace_id).select_related("actor")
    if event_type:
        queryset = queryset.filter(event_type=event_type)
    if since:
        queryset = queryset.filter(created_at__gte=since)
    if until:
        queryset = queryset.filter(created_at__lte=until)
    return queryset
