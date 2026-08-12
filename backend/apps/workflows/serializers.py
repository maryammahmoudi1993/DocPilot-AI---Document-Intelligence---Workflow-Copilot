from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.workflows.models import (
    NodeType,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
    WorkflowRun,
    WorkflowStepRun,
    WorkflowVersion,
)


class WorkflowNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowNode
        fields = ["node_key", "node_type", "kind", "config", "position"]


class WorkflowEdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowEdge
        fields = ["source_node_key", "target_node_key", "branch"]


class WorkflowVersionSerializer(serializers.ModelSerializer):
    nodes = WorkflowNodeSerializer(many=True, read_only=True)
    edges = WorkflowEdgeSerializer(many=True, read_only=True)

    class Meta:
        model = WorkflowVersion
        fields = ["id", "version_number", "status", "nodes", "edges", "created_at", "activated_at"]
        read_only_fields = fields


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = ["id", "name", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]


class WorkflowDetailSerializer(serializers.ModelSerializer):
    active_version = WorkflowVersionSerializer(read_only=True)
    draft_version = serializers.SerializerMethodField()

    @extend_schema_field(WorkflowVersionSerializer(allow_null=True))
    def get_draft_version(self, obj: Workflow) -> dict | None:
        from apps.workflows.selectors import get_draft_version

        draft = get_draft_version(workflow=obj)
        return WorkflowVersionSerializer(draft).data if draft else None

    class Meta:
        model = Workflow
        fields = [
            "id",
            "name",
            "is_active",
            "active_version",
            "draft_version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class WorkflowCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=1, max_length=255)


class DraftNodeRequestSerializer(serializers.Serializer):
    node_key = serializers.CharField(max_length=64)
    node_type = serializers.ChoiceField(choices=NodeType.choices)
    kind = serializers.CharField(max_length=64)
    config = serializers.DictField(required=False, default=dict)
    position = serializers.DictField(required=False, default=dict)


class DraftEdgeRequestSerializer(serializers.Serializer):
    source_node_key = serializers.CharField(max_length=64)
    target_node_key = serializers.CharField(max_length=64)
    branch = serializers.CharField(max_length=8, required=False, allow_blank=True, default="")


class SaveDraftRequestSerializer(serializers.Serializer):
    nodes = DraftNodeRequestSerializer(many=True)
    edges = DraftEdgeRequestSerializer(many=True)


class WorkflowStepRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStepRun
        fields = [
            "id",
            "node_key",
            "node_kind",
            "status",
            "output",
            "error_code",
            "attempt_count",
            "started_at",
            "completed_at",
        ]
        read_only_fields = fields


class WorkflowRunSerializer(serializers.ModelSerializer):
    step_runs = WorkflowStepRunSerializer(many=True, read_only=True)

    class Meta:
        model = WorkflowRun
        fields = [
            "id",
            "status",
            "trigger_context",
            "is_test_run",
            "error_code",
            "step_runs",
            "started_at",
            "completed_at",
            "created_at",
        ]
        read_only_fields = fields


class TestRunRequestSerializer(serializers.Serializer):
    trigger_context = serializers.DictField(required=False, default=dict)
