from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.workspaces.models import (
    ASSIGNABLE_ROLES,
    Workspace,
    WorkspaceMembership,
    WorkspaceSettings,
)


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ["id", "name", "slug"]
        read_only_fields = fields


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = WorkspaceMembership
        fields = ["id", "user", "role", "created_at"]
        read_only_fields = fields


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=[(r.value, r.label) for r in ASSIGNABLE_ROLES])


class ChangeRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[(r.value, r.label) for r in ASSIGNABLE_ROLES])


class TransferOwnershipSerializer(serializers.Serializer):
    new_owner_membership_id = serializers.UUIDField()


class WorkspaceSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceSettings
        fields = [
            "notify_on_approval_requested",
            "notify_on_document_processed",
            "webhook_notifications_enabled",
            "auto_classify_enabled",
            "document_retention_days",
            "raw_text_retention_days",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class WorkspaceSettingsUpdateSerializer(serializers.Serializer):
    notify_on_approval_requested = serializers.BooleanField(required=False)
    notify_on_document_processed = serializers.BooleanField(required=False)
    webhook_notifications_enabled = serializers.BooleanField(required=False)
    auto_classify_enabled = serializers.BooleanField(required=False)
    document_retention_days = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    raw_text_retention_days = serializers.IntegerField(required=False, allow_null=True, min_value=1)
