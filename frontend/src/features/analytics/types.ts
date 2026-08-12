export interface DashboardSummary {
  total_documents: number;
  documents_processing: number;
  documents_needing_review: number;
  pending_approvals: number;
  failed_jobs: number;
}

export interface ProcessingTrendPoint {
  date: string;
  total: number;
  completed: number;
  failed: number;
}

export interface DocumentTypeCount {
  document_type: string | null;
  count: number;
}

export interface ExtractionAccuracyMetrics {
  average_confidence: number | null;
  total_extractions: number;
  extractions_with_validation_errors: number;
  is_illustrative: boolean;
}

export interface ReviewRateMetrics {
  total_extractions: number;
  reviewed_count: number;
  review_rate: number | null;
}

export interface WorkflowSuccessMetrics {
  total_runs: number;
  succeeded: number;
  failed: number;
  success_rate: number | null;
}

export interface ApprovalDurationMetrics {
  average_duration_seconds: number | null;
}

export interface AnalyticsOverview {
  since: string;
  until: string;
  processing_trends: ProcessingTrendPoint[];
  document_type_counts: DocumentTypeCount[];
  extraction_accuracy: ExtractionAccuracyMetrics;
  review_rate: ReviewRateMetrics;
  workflow_success: WorkflowSuccessMetrics;
  approval_duration: ApprovalDurationMetrics;
}

export interface AnalyticsDateRange {
  since?: string;
  until?: string;
}
