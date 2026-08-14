"""Seeds the demo workspace with the synthetic sample documents (see
apps/documents/fixtures/README.md for provenance) so the primary demo
flow (upload -> processing -> extraction -> review -> approval -> RAG ->
workflow) has something real to run against. Requires `seed_demo_data`
to have already created the demo workspace and its owner user.
"""

from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.documents.services import create_document
from apps.workspaces.models import Workspace

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"

SAMPLE_FILES = [
    ("sample-invoice.pdf", "application/pdf"),
    ("sample-contract.pdf", "application/pdf"),
]


class Command(BaseCommand):
    help = "Upload the synthetic sample invoice/contract into the demo workspace (idempotent)."

    def handle(self, *args, **options):
        try:
            workspace = Workspace.objects.get(slug="demo-workspace")
        except Workspace.DoesNotExist as exc:
            raise CommandError(
                "Demo workspace not found — run `python manage.py seed_demo_data` first."
            ) from exc

        try:
            uploaded_by = User.objects.get(email="owner@demo.docpilot.ai")
        except User.DoesNotExist as exc:
            raise CommandError(
                "Demo owner user not found — run `python manage.py seed_demo_data` first."
            ) from exc

        for filename, content_type in SAMPLE_FILES:
            file_bytes = (FIXTURES_DIR / filename).read_bytes()
            uploaded_file = SimpleUploadedFile(filename, file_bytes, content_type=content_type)
            try:
                document = create_document(
                    workspace=workspace, uploaded_by=uploaded_by, uploaded_file=uploaded_file
                )
            except Exception as exc:  # noqa: BLE001 - duplicate-content is the expected re-run case
                # create_document raises ValidationError with an
                # `existing_document_id` when this exact file content
                # already exists in the workspace — that's the expected
                # outcome on a second run, not a real failure.
                if "existing_document_id" in getattr(exc, "message_dict", {}):
                    self.stdout.write(f"  Already seeded: {filename}")
                    continue
                raise
            self.stdout.write(f"  Created document: {document.filename} ({document.id})")

        self.stdout.write(self.style.SUCCESS("Demo documents seeded."))
