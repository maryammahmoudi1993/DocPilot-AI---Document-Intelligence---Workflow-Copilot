from rest_framework import serializers


class DashboardSummarySerializer(serializers.Serializer):
    total_documents = serializers.IntegerField()
    documents_processing = serializers.IntegerField()
    documents_needing_review = serializers.IntegerField()
    pending_approvals = serializers.IntegerField()
    failed_jobs = serializers.IntegerField()


class ProcessingTrendPointSerializer(serializers.Serializer):
    date = serializers.CharField()
    total = serializers.IntegerField()
    completed = serializers.IntegerField()
    failed = serializers.IntegerField()


class DocumentTypeCountSerializer(serializers.Serializer):
    document_type = serializers.CharField()
    count = serializers.IntegerField()


class ExtractionAccuracyMetricsSerializer(serializers.Serializer):
    average_confidence = serializers.FloatField(allow_null=True)
    total_extractions = serializers.IntegerField()
    extractions_with_validation_errors = serializers.IntegerField()
    is_illustrative = serializers.BooleanField()


class ReviewRateMetricsSerializer(serializers.Serializer):
    total_extractions = serializers.IntegerField()
    reviewed_count = serializers.IntegerField()
    review_rate = serializers.FloatField(allow_null=True)


class WorkflowSuccessMetricsSerializer(serializers.Serializer):
    total_runs = serializers.IntegerField()
    succeeded = serializers.IntegerField()
    failed = serializers.IntegerField()
    success_rate = serializers.FloatField(allow_null=True)


class ApprovalDurationMetricsSerializer(serializers.Serializer):
    average_duration_seconds = serializers.FloatField(allow_null=True)


class AnalyticsOverviewSerializer(serializers.Serializer):
    """Everything the Analytics page needs in one request — avoids six
    separate round trips for what's rendered as one dashboard of
    charts."""

    since = serializers.CharField()
    until = serializers.CharField()
    processing_trends = ProcessingTrendPointSerializer(many=True)
    document_type_counts = DocumentTypeCountSerializer(many=True)
    extraction_accuracy = ExtractionAccuracyMetricsSerializer()
    review_rate = ReviewRateMetricsSerializer()
    workflow_success = WorkflowSuccessMetricsSerializer()
    approval_duration = ApprovalDurationMetricsSerializer()
