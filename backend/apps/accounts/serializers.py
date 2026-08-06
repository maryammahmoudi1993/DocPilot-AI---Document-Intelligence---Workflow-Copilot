from rest_framework import serializers

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class WorkspaceMembershipSummarySerializer(serializers.Serializer):
    """Used inside the session payload — a lightweight
    workspace-plus-my-role view, not the full membership resource (that's
    apps.workspaces.serializers.MembershipSerializer, used by the
    membership-management endpoints)."""

    id = serializers.UUIDField(source="workspace.id")
    name = serializers.CharField(source="workspace.name")
    slug = serializers.CharField(source="workspace.slug")
    role = serializers.CharField()


class SessionSerializer(serializers.Serializer):
    user = UserSerializer()
    workspaces = WorkspaceMembershipSummarySerializer(many=True)
    active_workspace_id = serializers.UUIDField(allow_null=True)


class ActiveWorkspaceSerializer(serializers.Serializer):
    workspace_id = serializers.UUIDField()
