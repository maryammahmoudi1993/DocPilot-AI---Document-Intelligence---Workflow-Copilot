from typing import Any

from apps.audit.models import AuditEvent


def record_event(
    *,
    event_type: str,
    actor=None,
    workspace=None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Single entry point for writing audit events. `metadata` must never
    contain secrets/tokens/passwords — see AuditEvent's docstring."""
    return AuditEvent.objects.create(
        event_type=event_type,
        actor=actor,
        workspace=workspace,
        metadata=metadata or {},
    )
