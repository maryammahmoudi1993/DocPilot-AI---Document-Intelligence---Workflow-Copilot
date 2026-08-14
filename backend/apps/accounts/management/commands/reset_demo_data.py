"""Wipes every workspace-scoped row for the demo workspace and rebuilds
the base seed (workspace, demo users, memberships) — the "reset" a demo
operator runs between showings so leftover uploads/approvals/workflow
runs from a previous demo never leak into the next one.

Deliberately narrower than "delete the workspace and recreate it": the
demo workspace's id and the demo users' credentials must stay stable
across a reset (nothing referencing them by id — a bookmarked URL, a
previously-issued JWT — should break just because the demo was reset).
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.approvals.models import ApprovalRequest
from apps.assistant.models import Conversation
from apps.audit.models import AuditEvent
from apps.documents.models import Document
from apps.notifications.models import Notification, WebhookEndpoint
from apps.processing.models import ProcessingJob
from apps.workflows.models import Workflow
from apps.workspaces.models import Workspace


class Command(BaseCommand):
    help = "Clear the demo workspace's content and rebuild the base demo seed (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        workspace = Workspace.objects.filter(slug="demo-workspace").first()
        if workspace is not None:
            # Order matters where a FK isn't CASCADE (ApprovalRequest.document
            # is SET_NULL, so it must be cleared explicitly rather than
            # relying on Document's cascade). ProcessingJob/DocumentExtraction
            # cascade from Document and don't need a separate call.
            ApprovalRequest.objects.filter(workspace=workspace).delete()
            Workflow.objects.filter(workspace=workspace).delete()
            Notification.objects.filter(workspace=workspace).delete()
            WebhookEndpoint.objects.filter(workspace=workspace).delete()
            Conversation.objects.filter(workspace=workspace).delete()
            ProcessingJob.objects.filter(workspace=workspace).delete()
            Document.objects.filter(workspace=workspace).delete()
            AuditEvent.objects.filter(workspace=workspace).delete()
            self.stdout.write(f"Cleared workspace-scoped content for {workspace.name}")
        else:
            self.stdout.write("No existing demo workspace found — nothing to clear")

        call_command("seed_demo_data")
        self.stdout.write(self.style.SUCCESS("Demo data reset complete."))
