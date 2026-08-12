import { useNavigate } from 'react-router-dom';
import { AlertTriangle, CheckSquare, Clock, FileText, Loader2, Upload } from 'lucide-react';
import { useSession } from '@/features/auth/hooks';
import { useDashboardSummary } from '@/features/analytics/hooks';
import { useDocuments } from '@/features/documents/hooks';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/Button';
import { MetricCard } from '@/components/ui/MetricCard';
import { DocumentStatusBadge } from '@/components/documents/DocumentStatusBadge';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';

export function DashboardPage() {
  const navigate = useNavigate();
  const { data: session } = useSession();
  const workspaceId = session?.active_workspace_id ?? undefined;
  const firstName = session?.user?.first_name;

  const summaryQuery = useDashboardSummary(workspaceId);
  const recentDocumentsQuery = useDocuments(workspaceId, {
    ordering: '-created_at',
    page_size: 5,
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={firstName ? `Welcome back, ${firstName}` : 'Dashboard'}
        description="Overview of this workspace's document activity."
        actions={
          <Button onClick={() => navigate('/app/documents')}>
            <Upload className="h-4 w-4" aria-hidden="true" />
            Upload document
          </Button>
        }
      />

      {summaryQuery.isPending && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28 w-full rounded-lg" />
          ))}
        </div>
      )}

      {summaryQuery.isError && (
        <ErrorState description="Could not load the dashboard summary." onRetry={() => summaryQuery.refetch()} />
      )}

      {summaryQuery.data && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <MetricCard
            label="Total documents"
            value={String(summaryQuery.data.total_documents)}
            icon={FileText}
            isSample={false}
          />
          <MetricCard
            label="Processing"
            value={String(summaryQuery.data.documents_processing)}
            icon={Loader2}
            isSample={false}
          />
          <MetricCard
            label="Needs review"
            value={String(summaryQuery.data.documents_needing_review)}
            icon={Clock}
            isSample={false}
          />
          <MetricCard
            label="Pending approvals"
            value={String(summaryQuery.data.pending_approvals)}
            icon={CheckSquare}
            isSample={false}
          />
          <MetricCard
            label="Failed jobs"
            value={String(summaryQuery.data.failed_jobs)}
            icon={AlertTriangle}
            isSample={false}
          />
        </div>
      )}

      <div className="rounded-lg border border-border bg-card">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold text-text-primary">Recent documents</h2>
          <Button variant="ghost" size="sm" onClick={() => navigate('/app/documents')}>
            View all
          </Button>
        </div>

        {recentDocumentsQuery.isPending && (
          <div className="flex flex-col gap-2 p-5">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-12 w-full rounded-md" />
            ))}
          </div>
        )}

        {recentDocumentsQuery.isError && (
          <div className="p-5">
            <ErrorState
              description="Could not load recent documents."
              onRetry={() => recentDocumentsQuery.refetch()}
            />
          </div>
        )}

        {recentDocumentsQuery.data && recentDocumentsQuery.data.results.length === 0 && (
          <div className="p-5">
            <EmptyState
              icon={FileText}
              title="No documents yet"
              description="Upload your first document to see it here."
            />
          </div>
        )}

        {recentDocumentsQuery.data && recentDocumentsQuery.data.results.length > 0 && (
          <ul>
            {recentDocumentsQuery.data.results.map((document) => (
              <li
                key={document.id}
                className="flex items-center justify-between gap-4 border-b border-border px-5 py-3 last:border-b-0"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-text-primary">
                    {document.filename}
                  </p>
                  <p className="mt-0.5 text-xs text-text-secondary">
                    {new Date(document.created_at).toLocaleDateString()}
                  </p>
                </div>
                <DocumentStatusBadge status={document.status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
