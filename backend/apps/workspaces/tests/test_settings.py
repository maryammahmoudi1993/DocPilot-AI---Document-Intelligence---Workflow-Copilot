import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.workspaces import services
from apps.workspaces.models import Role, WorkspaceSettings
from tests.factories import UserFactory, WorkspaceFactory, WorkspaceMembershipFactory


@pytest.mark.django_db
class TestGetOrCreateSettings:
    def test_creates_a_row_with_sensible_defaults_on_first_read(self):
        workspace = WorkspaceFactory()

        settings_row = services.get_or_create_settings(workspace=workspace)

        assert settings_row.auto_classify_enabled is True
        assert settings_row.document_retention_days is None
        assert WorkspaceSettings.objects.filter(workspace=workspace).count() == 1

    def test_is_idempotent(self):
        workspace = WorkspaceFactory()

        first = services.get_or_create_settings(workspace=workspace)
        second = services.get_or_create_settings(workspace=workspace)

        assert first.id == second.id
        assert WorkspaceSettings.objects.filter(workspace=workspace).count() == 1


@pytest.mark.django_db
class TestUpdateSettings:
    def test_updates_the_given_fields_and_records_an_audit_event(self):
        from apps.audit.models import AuditEvent

        workspace = WorkspaceFactory()
        actor = WorkspaceMembershipFactory(workspace=workspace, role=Role.OWNER)

        updated = services.update_settings(
            workspace=workspace, actor_membership=actor, auto_classify_enabled=False
        )

        assert updated.auto_classify_enabled is False
        assert AuditEvent.objects.filter(event_type="workspace.settings_updated").exists()

    def test_rejects_a_retention_value_below_one_day(self):
        workspace = WorkspaceFactory()
        actor = WorkspaceMembershipFactory(workspace=workspace, role=Role.OWNER)

        with pytest.raises(ValidationError):
            services.update_settings(
                workspace=workspace, actor_membership=actor, document_retention_days=0
            )

    def test_null_retention_means_keep_indefinitely_and_is_accepted(self):
        workspace = WorkspaceFactory()
        actor = WorkspaceMembershipFactory(workspace=workspace, role=Role.OWNER)
        services.update_settings(
            workspace=workspace, actor_membership=actor, document_retention_days=30
        )

        updated = services.update_settings(
            workspace=workspace, actor_membership=actor, document_retention_days=None
        )

        assert updated.document_retention_days is None


@pytest.mark.django_db
class TestWorkspaceSettingsView:
    def _client_with_role(self, api_client, workspace, role):
        user = UserFactory()
        WorkspaceMembershipFactory(user=user, workspace=workspace, role=role)
        api_client.force_authenticate(user=user)
        return user

    def test_any_member_can_read_settings(self, api_client):
        workspace = WorkspaceFactory()
        self._client_with_role(api_client, workspace, Role.VIEWER)

        response = api_client.get(reverse("workspace-settings", args=[workspace.id]))

        assert response.status_code == 200
        assert response.data["auto_classify_enabled"] is True

    def test_a_viewer_cannot_update_settings(self, api_client):
        workspace = WorkspaceFactory()
        self._client_with_role(api_client, workspace, Role.VIEWER)

        response = api_client.patch(
            reverse("workspace-settings", args=[workspace.id]),
            {"auto_classify_enabled": False},
            format="json",
        )

        assert response.status_code == 403

    def test_an_admin_can_update_settings(self, api_client):
        workspace = WorkspaceFactory()
        self._client_with_role(api_client, workspace, Role.ADMIN)

        response = api_client.patch(
            reverse("workspace-settings", args=[workspace.id]),
            {"notify_on_approval_requested": False, "document_retention_days": 90},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["notify_on_approval_requested"] is False
        assert response.data["document_retention_days"] == 90

    def test_an_invalid_retention_value_returns_400(self, api_client):
        workspace = WorkspaceFactory()
        self._client_with_role(api_client, workspace, Role.ADMIN)

        response = api_client.patch(
            reverse("workspace-settings", args=[workspace.id]),
            {"document_retention_days": 0},
            format="json",
        )

        assert response.status_code == 400

    def test_anonymous_is_rejected(self, api_client):
        workspace = WorkspaceFactory()

        response = api_client.get(reverse("workspace-settings", args=[workspace.id]))

        assert response.status_code == 401
