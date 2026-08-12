import { ClipboardCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useSession } from '@/features/auth/hooks';
import { useExtractionQueue } from '@/features/extraction/hooks';
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { FullPageSpinner } from '@/components/ui/FullPageSpinner';

export function ReviewQueuePage() {
  const { data: session } = useSession();
  const workspaceId = session?.active_workspace_id ?? undefined;
  const { data: queue, isLoading, isError, refetch } = useExtractionQueue(workspaceId);

  if (isLoading || !workspaceId) {
    return <FullPageSpinner />;
  }

  if (isError) {
    return <ErrorState title="Couldn't load the review queue" onRetry={() => void refetch()} />;
  }

  if (!queue || queue.length === 0) {
    return (
      <EmptyState
        icon={ClipboardCheck}
        title="Nothing waiting on review"
        description="Invoices that need a human look — missing fields, arithmetic mismatches, or low-confidence extractions — will show up here."
      />
    );
  }

  return (
    <div className="p-6">
      <h1 className="mb-4 text-lg font-semibold text-text-primary">Review Queue</h1>
      <div className="divide-y divide-divider rounded-lg border border-border bg-card">
        {queue.map((item) => (
          <Link
            key={item.id}
            to={`/app/documents/${item.document_id}/review`}
            className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-lavender focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <div>
              <p className="text-sm font-medium text-text-primary">{item.filename}</p>
              <p className="text-xs text-text-secondary">
                {item.error_issue_count > 0
                  ? `${item.error_issue_count} issue${item.error_issue_count === 1 ? '' : 's'} to resolve`
                  : 'Ready for review'}
              </p>
            </div>
            {item.overall_confidence !== null && <ConfidenceBadge score={item.overall_confidence} />}
          </Link>
        ))}
      </div>
    </div>
  );
}
