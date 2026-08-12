/** Mirrors backend/apps/extraction/models.py and serializers.py exactly. */

export type ExtractionStatus = 'pending_review' | 'approved' | 'rejected';

export type ValidationSeverity = 'error' | 'warning';

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface FieldCorrection {
  id: string;
  before_value: string;
  after_value: string;
  reason: string;
  corrected_by_email: string | null;
  corrected_at: string;
}

export interface ExtractedField {
  id: string;
  key: string;
  label: string;
  display_value: string;
  normalized_value: string;
  confidence: number | null;
  is_required: boolean;
  page_number: number | null;
  bounding_box: BoundingBox | null;
  corrections: FieldCorrection[];
}

export interface ValidationIssue {
  id: string;
  field_key: string | null;
  code: string;
  message: string;
  severity: ValidationSeverity;
}

export interface DocumentExtraction {
  id: string;
  document_id: string;
  document_type: string;
  status: ExtractionStatus;
  version: number;
  overall_confidence: number | null;
  fields_data: ExtractedField[];
  issues: ValidationIssue[];
  reviewed_by_email: string | null;
  reviewed_at: string | null;
  approved_by_email: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

/** Matches `ExtractionQueueItemSerializer` — the lightweight row shape
 * the Review Queue list endpoint returns. */
export interface ExtractionQueueItem {
  id: string;
  document_id: string;
  filename: string;
  document_type: string;
  status: ExtractionStatus;
  overall_confidence: number | null;
  error_issue_count: number;
  created_at: string;
}

export interface FieldCorrectionRequest {
  value: string;
  reason?: string;
  expected_version: number;
}

export interface StatusTransitionRequest {
  status: ExtractionStatus;
  expected_version: number;
}
