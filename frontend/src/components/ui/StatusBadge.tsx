import { cn } from '@/lib/utils';

export type DocumentStatus = 'processing' | 'approved' | 'needs_review' | 'failed';

const STATUS_LABEL: Record<DocumentStatus, string> = {
  processing: 'Processing',
  approved: 'Approved',
  needs_review: 'Needs Review',
  failed: 'Failed',
};

const STATUS_CLASSES: Record<DocumentStatus, string> = {
  processing: 'bg-status-processing-bg text-status-processing',
  approved: 'bg-status-approved-bg text-status-approved',
  needs_review: 'bg-status-review-bg text-status-review',
  failed: 'bg-status-failed-bg text-status-failed',
};

export interface StatusBadgeProps {
  status: DocumentStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
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
