import { Button } from '@/components/ui/Button';
import { useProcessingStatus, useRetryProcessing } from '@/features/processing/hooks';
import { STAGE_LABEL } from '@/features/processing/labels';
import { ProcessingStatusBadge } from './ProcessingStatusBadge';

export interface ProcessingStatusInlineProps {
  workspaceId: string | undefined;
  documentId: string;
}

/**
 * Tracks one document's async processing pipeline (Phase 4) from right
 * after its upload finishes — polls with backoff until COMPLETED or
 * FAILED (see useProcessingStatus), then stops. Shown inline in the
 * upload dialog's queue (see UploadDialog.tsx) rather than as a
 * separate screen, since that's the one place the frontend currently
 * has a concrete, just-created document id to track; the main
 * Documents table doesn't poll per-row processing status (see the
 * Phase 4 completion report's known limitations).
 */
export function ProcessingStatusInline({ workspaceId, documentId }: ProcessingStatusInlineProps) {
  const { data: job, isLoading, isError } = useProcessingStatus(workspaceId, documentId);
  const retryProcessing = useRetryProcessing(workspaceId, documentId);

  if (isLoading || !job) {
    return (
      <div className="mt-1.5 flex items-center gap-2 text-xs text-text-muted">
        <span role="status">Checking processing status…</span>
      </div>
    );
  }

  if (isError) {
    return <p className="mt-1.5 text-xs text-status-failed">Couldn't check processing status.</p>;
  }

  // Only show the fine-grained stage name separately when it says more
  // than the badge already does — for queued/completed/failed the two
  // labels are identical, so a second copy would just be noise (and,
  // worse, an ambiguous duplicate for anything querying by text).
  const showStageDetail = !['queued', 'completed', 'failed'].includes(job.stage);

  return (
    <div className="mt-1.5 space-y-1">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ProcessingStatusBadge stage={job.stage} />
          {showStageDetail && <span className="text-xs text-text-secondary">{STAGE_LABEL[job.stage]}</span>}
        </div>
        {job.stage === 'failed' && job.is_retryable && (
          <Button
            variant="secondary"
            size="sm"
            aria-label="Retry processing"
            onClick={() => retryProcessing.mutate()}
            isLoading={retryProcessing.isPending}
          >
            Retry
          </Button>
        )}
      </div>
      {job.stage === 'failed' && job.error_message && (
        <p className="text-xs text-status-failed">{job.error_message}</p>
      )}
    </div>
  );
}
