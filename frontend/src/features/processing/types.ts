/** Mirrors backend/apps/processing/models.py's ProcessingStage exactly
 * — see ProcessingJobSerializer for the response shape this matches. */
export type ProcessingStage =
  | 'queued'
  | 'validating'
  | 'extracting_text'
  | 'running_ocr'
  | 'classifying'
  | 'extracting_fields'
  | 'validating_extraction'
  | 'scoring_confidence'
  | 'indexing'
  | 'completed'
  | 'failed';

export const TERMINAL_STAGES: readonly ProcessingStage[] = ['completed', 'failed'];

export interface ProcessingStageEvent {
  stage: ProcessingStage;
  status: 'started' | 'completed' | 'skipped' | 'failed';
  detail: string;
  at: string;
}

export interface ProcessingJob {
  id: string;
  document_id: string;
  stage: ProcessingStage;
  attempt_count: number;
  is_retryable: boolean;
  error_code: string | null;
  error_message: string | null;
  document_type: string | null;
  total_pages: number | null;
  ocr_page_count: number;
  stage_history: ProcessingStageEvent[];
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}
