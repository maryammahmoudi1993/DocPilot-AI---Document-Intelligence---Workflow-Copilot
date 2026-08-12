import { Button } from '@/components/ui/Button';
import type { ExtractionStatus } from '@/features/extraction/types';

export interface ReviewActionBarProps {
  status: ExtractionStatus;
  canApprove: boolean;
  canReject: boolean;
  isSubmitting: boolean;
  blockedByErrors: boolean;
  onApprove: () => void;
  onReject: () => void;
  onRequestReview: () => void;
}

/** Sticky bottom action area — matches the reference layout's pattern
 * of keeping the primary decision always reachable without scrolling
 * back up. Per-field saves happen inline (see ExtractionFieldRow); this
 * bar only holds the extraction-level status transitions. */
export function ReviewActionBar({
  status,
  canApprove,
  canReject,
  isSubmitting,
  blockedByErrors,
  onApprove,
  onReject,
  onRequestReview,
}: ReviewActionBarProps) {
  return (
    <div className="sticky bottom-0 flex items-center justify-end gap-2 border-t border-border bg-card px-4 py-3">
      {status === 'rejected' && canReject && (
        <Button type="button" variant="secondary" isLoading={isSubmitting} onClick={onRequestReview}>
          Send back for review
        </Button>
      )}
      {status === 'pending_review' && (
        <>
          {canReject && (
            <Button type="button" variant="destructive" isLoading={isSubmitting} onClick={onReject}>
              Reject
            </Button>
          )}
          {canApprove && (
            <Button
              type="button"
              variant="primary"
              isLoading={isSubmitting}
              disabled={blockedByErrors}
              title={blockedByErrors ? 'Resolve validation errors before approving.' : undefined}
              onClick={onApprove}
            >
              Approve
            </Button>
          )}
        </>
      )}
      {status === 'approved' && <p className="text-sm text-text-secondary">This extraction has been approved.</p>}
    </div>
  );
}
