from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.workspaces.models import ASSIGNABLE_ROLES, Workspace, WorkspaceMembership


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
