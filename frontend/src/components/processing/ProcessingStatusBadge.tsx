import { cn } from '@/lib/utils';
import type { ProcessingStage } from '@/features/processing/types';

/** Coarse grouping for the badge's color — the fine-grained current
 * stage (e.g. "Running OCR") is shown as separate text next to the
 * badge (see ProcessingStatusInline), not baked into the badge itself,
 * so the badge stays a stable visual anchor while the stage text
 * updates underneath it as polling progresses. */
type BadgeGroup = 'queued' | 'processing' | 'completed' | 'failed';

const GROUP_BY_STAGE: Record<ProcessingStage, BadgeGroup> = {
  queued: 'queued',
  validating: 'processing',
  extracting_text: 'processing',
  running_ocr: 'processing',
  classifying: 'processing',
  extracting_fields: 'processing',
  validating_extraction: 'processing',
  scoring_confidence: 'processing',
  indexing: 'processing',
  completed: 'completed',
  failed: 'failed',
};

const GROUP_LABEL: Record<BadgeGroup, string> = {
  queued: 'Queued',
  processing: 'Processing',
  completed: 'Processed',
  failed: 'Failed',
};

const GROUP_CLASSES: Record<BadgeGroup, string> = {
  queued: 'bg-status-processing-bg text-status-processing',
  processing: 'bg-status-processing-bg text-status-processing',
  completed: 'bg-status-approved-bg text-status-approved',
  failed: 'bg-status-failed-bg text-status-failed',
};

export interface ProcessingStatusBadgeProps {
  stage: ProcessingStage;
  className?: string;
}

export function ProcessingStatusBadge({ stage, className }: ProcessingStatusBadgeProps) {
  const group = GROUP_BY_STAGE[stage];
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        GROUP_CLASSES[group],
        className,
      )}
    >
      {GROUP_LABEL[group]}
    </span>
  );
}
