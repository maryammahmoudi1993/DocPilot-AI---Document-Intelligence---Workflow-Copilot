from rest_framework import serializers

from apps.approvals.models import ApprovalComment, ApprovalRequest


class ApprovalCommentSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True, allow_null=True)

    class Meta:
        model = ApprovalComment
        fields = ["id", "author_email", "body", "created_at"]
        read_only_fields = fields


class ApprovalRequestSerializer(serializers.ModelSerializer):
    comments = ApprovalCommentSerializer(many=True, read_only=True)
    requested_by_email = serializers.EmailField(
        source="requested_by.email", read_only=True, allow_null=True
    )
    decided_by_email = serializers.EmailField(
        source="decided_by.email", read_only=True, allow_null=True
    )
    document_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = ApprovalRequest
        fields = [
            "id",
            "title",
            "description",
            "risk_level",
            "status",
            "assigned_role",
            "document_id",
            "requested_by_email",
            "decided_by_email",
            "decided_at",
            "expires_at",
            "comments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ApprovalDecisionRequestSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["approved", "rejected"])
    reason = serializers.CharField(required=False, allow_blank=True, default="", max_length=500)


class ApprovalCommentRequestSerializer(serializers.Serializer):
    body = serializers.CharField(min_length=1, max_length=2000)
