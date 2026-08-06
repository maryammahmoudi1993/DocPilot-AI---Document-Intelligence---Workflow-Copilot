"""Deterministic demo user/workspace/membership seed data.

Portfolio demonstration only — DEMO_PASSWORD below is intentionally
public (printed to stdout, documented in the README); it is not a real
secret and must never be reused for a real account.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.workspaces.models import Role, Workspace, WorkspaceMembership

DEMO_PASSWORD = "DemoWorkspace!2026"  # noqa: S105 - intentionally public demo credential

DEMO_USERS = [
    ("owner@demo.docpilot.ai", "Demo", "Owner", Role.OWNER),
    ("admin@demo.docpilot.ai", "Demo", "Admin", Role.ADMIN),
    ("finance@demo.docpilot.ai", "Demo", "Finance Manager", Role.FINANCE_MANAGER),
    ("reviewer@demo.docpilot.ai", "Demo", "Reviewer", Role.REVIEWER),
    ("viewer@demo.docpilot.ai", "Demo", "Viewer", Role.VIEWER),
]


class Command(BaseCommand):
    help = "Create deterministic demo workspace, users, and memberships (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        workspace, created = Workspace.objects.get_or_create(
            slug="demo-workspace", defaults={"name": "Demo Workspace"}
        )
        self.stdout.write(f"{'Created' if created else 'Found'} workspace: {workspace.name}")

        for email, first_name, last_name, role in DEMO_USERS:
            # get_or_create() constructs the model directly on a cache
            # miss — it does not go through UserManager.create_user(), so
            # username (unique, and not auto-derived from email outside
            # that manager method) must be set explicitly here too.
            user, user_created = User.objects.get_or_create(
                email=email,
                defaults={"username": email, "first_name": first_name, "last_name": last_name},
            )
            if user_created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])

            membership, membership_created = WorkspaceMembership.objects.get_or_create(
                workspace=workspace, user=user, defaults={"role": role}
            )
            if user_created and role == Role.OWNER:
                user.active_workspace = workspace
                user.save(update_fields=["active_workspace"])

            self.stdout.write(
                f"  {'Created' if user_created else 'Found'} user {email} "
                f"({'created' if membership_created else 'existing'} {role} membership)"
            )

        self.stdout.write(
            self.style.SUCCESS(f"Demo password for all seeded users: {DEMO_PASSWORD}")
        )
