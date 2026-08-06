import pytest
from django.core.management import call_command

from apps.accounts.models import User
from apps.workspaces.models import Role, Workspace, WorkspaceMembership


@pytest.mark.django_db
def test_seed_demo_data_creates_workspace_users_and_memberships():
    call_command("seed_demo_data")

    workspace = Workspace.objects.get(slug="demo-workspace")
    assert User.objects.filter(email="owner@demo.docpilot.ai").exists()
    assert WorkspaceMembership.objects.filter(
        workspace=workspace, user__email="owner@demo.docpilot.ai", role=Role.OWNER
    ).exists()
    assert WorkspaceMembership.objects.filter(workspace=workspace).count() == 5


@pytest.mark.django_db
def test_seed_demo_data_is_idempotent():
    call_command("seed_demo_data")
    call_command("seed_demo_data")

    assert Workspace.objects.filter(slug="demo-workspace").count() == 1
    assert WorkspaceMembership.objects.count() == 5
