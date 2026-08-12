from rest_framework import serializers

from apps.extraction.models import (
    DocumentExtraction,
    ExtractedField,
    FieldCorrection,
    ValidationIssue,
)


class FieldCorrectionSerializer(serializers.ModelSerializer):
    corrected_by_email = serializers.EmailField(source="corrected_by.email", read_only=True)

    class Meta:
        model = FieldCorrection
        fields = [
            "id",
            "before_value",
            "after_value",
            "reason",
            "corrected_by_email",
            "corrected_at",
        ]
        read_only_fields = fields


class ExtractedFieldSerializer(serializers.ModelSerializer):
    corrections = FieldCorrectionSerializer(many=True, read_only=True)

    class Meta:
        model = ExtractedField
        fields = [
            "id",
            "key",
            "label",
            "display_value",
            "normalized_value",
            "confidence",
            "is_required",
            "page_number",
            "bounding_box",
            "corrections",
        ]
        read_only_fields = fields


class ValidationIssueSerializer(serializers.ModelSerializer):
    field_key = serializers.CharField(source="field.key", read_only=True, allow_null=True)

    class Meta:
        model = ValidationIssue
        fields = ["id", "field_key", "code", "message", "severity"]
        read_only_fields = fields


class DocumentExtractionSerializer(serializers.ModelSerializer):
    fields_data = ExtractedFieldSerializer(source="fields", many=True, read_only=True)
    issues = ValidationIssueSerializer(many=True, read_only=True)
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True)
    approved_by_email = serializers.EmailField(source="approved_by.email", read_only=True)

    class Meta:
        model = DocumentExtraction
        fields = [
            "id",
            "document_id",
            "document_type",
            "status",
            "version",
            "overall_confidence",
            "fields_data",
            "issues",
            "reviewed_by_email",
            "reviewed_at",
            "approved_by_email",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class FieldCorrectionRequestSerializer(serializers.Serializer):
    value = serializers.CharField(allow_blank=True, max_length=500)
    reason = serializers.CharField(allow_blank=True, required=False, default="", max_length=255)
    expected_version = serializers.IntegerField(min_value=1)


class StatusTransitionRequestSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["approved", "rejected", "pending_review"])
    expected_version = serializers.IntegerField(min_value=1)
