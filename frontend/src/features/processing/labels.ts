import type { ProcessingStage } from './types';

/** Human-readable label per stage — split out from
 * components/processing/ProcessingStatusBadge.tsx so that component
 * module exports only the component itself (react-refresh/fast-refresh
 * requires component-only modules to hot-reload reliably). */
export const STAGE_LABEL: Record<ProcessingStage, string> = {
  queued: 'Queued',
  validating: 'Validating',
  extracting_text: 'Extracting text',
  running_ocr: 'Running OCR',
  classifying: 'Classifying',
  extracting_fields: 'Extracting structured data',
  validating_extraction: 'Validating extraction',
  scoring_confidence: 'Scoring confidence',
  indexing: 'Indexing',
  completed: 'Completed',
  failed: 'Failed',
};
