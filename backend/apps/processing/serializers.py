from rest_framework import serializers


class ProcessingStageEventSerializer(serializers.Serializer):
    stage = serializers.CharField()
    status = serializers.CharField()
    detail = serializers.CharField(allow_blank=True)
    at = serializers.CharField()


class ProcessingJobSerializer(serializers.Serializer):
    """Plain Serializer (not ModelSerializer) — deliberately excludes
    `raw_text_excerpt` (internal-debugging-only, never meant for the
    client; see the field's docstring on ProcessingJob) from the API
    surface entirely, which a ModelSerializer's field-list approach
    makes easy to get wrong by omission later."""

    id = serializers.UUIDField()
    document_id = serializers.UUIDField()
    stage = serializers.CharField()
    attempt_count = serializers.IntegerField()
    is_retryable = serializers.BooleanField()
    error_code = serializers.CharField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)
    document_type = serializers.CharField(allow_null=True)
    total_pages = serializers.IntegerField(allow_null=True)
    ocr_page_count = serializers.IntegerField()
    stage_history = ProcessingStageEventSerializer(many=True)
    created_at = serializers.DateTimeField()
    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
