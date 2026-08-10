import { cn } from '@/lib/utils';
import type { DocumentStatus } from '@/features/documents/types';

/**
 * The shared `StatusBadge` (components/ui/StatusBadge.tsx) covers the
 * later AI-review pipeline's statuses (processing/approved/needs_review/
 * failed), which don't exist yet — today's `Document` model only has
 * `uploaded`/`archived` (see backend/apps/documents/models.py). This is
 * a separate badge for those two real statuses rather than stretching
 * the review-pipeline badge to cover a state it doesn't model.
 */
const STATUS_LABEL: Record<DocumentStatus, string> = {
  uploaded: 'Uploaded',
  archived: 'Archived',
};

const STATUS_CLASSES: Record<DocumentStatus, string> = {
  uploaded: 'bg-status-approved-bg text-status-approved',
  archived: 'bg-lavender text-text-secondary',
};

export interface DocumentStatusBadgeProps {
  status: DocumentStatus;
  className?: string;
}

export function DocumentStatusBadge({ status, className }: DocumentStatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        STATUS_CLASSES[status],
        className,
      )}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}
