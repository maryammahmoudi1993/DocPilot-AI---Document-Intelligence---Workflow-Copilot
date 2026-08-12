import { useState } from 'react';
import { CheckSquare, MessageSquare } from 'lucide-react';
import { useSession } from '@/features/auth/hooks';
import {
  useAddApprovalComment,
  useApproval,
  useApprovals,
  useDecideApproval,
} from '@/features/approvals/hooks';
import type { ApprovalStatus, RiskLevel } from '@/features/approvals/types';
import { ApiError } from '@/lib/apiClient';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { ConfirmationDialog } from '@/components/ui/ConfirmationDialog';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { cn } from '@/lib/utils';

const STATUS_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'expired', label: 'Expired' },
];

const RISK_CLASSES: Record<RiskLevel, string> = {
  low: 'bg-status-approved-bg text-status-approved',
  medium: 'bg-status-review-bg text-status-review',
  high: 'bg-status-failed-bg text-status-failed',
};

const STATUS_CLASSES: Record<ApprovalStatus, string> = {
  pending: 'bg-status-processing-bg text-status-processing',
  approved: 'bg-status-approved-bg text-status-approved',
  rejected: 'bg-status-failed-bg text-status-failed',
  expired: 'bg-lavender text-text-secondary',
};

function Badge({ label, className }: { label: string; className: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize',
        className,
      )}
    >
      {label}
    </span>
  );
}

export function ApprovalsPage() {
  const { data: session } = useSession();
  const workspaceId = session?.active_workspace_id ?? undefined;

  const [statusFilter, setStatusFilter] = useState('all');
  const [activeApprovalId, setActiveApprovalId] = useState<string | null>(null);

  const status = statusFilter === 'all' ? undefined : (statusFilter as ApprovalStatus);
  const approvalsQuery = useApprovals(workspaceId, status);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Approvals"
        description="Review and act on high-value requests raised by workflows and teammates."
        actions={
          <Select
            options={STATUS_OPTIONS}
            value={statusFilter}
            onValueChange={setStatusFilter}
            aria-label="Filter by status"
            className="w-40"
          />
        }
      />

      {approvalsQuery.isPending && (
        <div className="flex flex-col gap-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      )}

      {approvalsQuery.isError && (
        <ErrorState
          description="Could not load approval requests."
          onRetry={() => approvalsQuery.refetch()}
        />
      )}

      {approvalsQuery.data && approvalsQuery.data.length === 0 && (
        <EmptyState
          icon={CheckSquare}
          title="No approval requests"
          description="Nothing is waiting on a decision right now."
        />
      )}

      {approvalsQuery.data && approvalsQuery.data.length > 0 && (
        <ul className="flex flex-col gap-2">
          {approvalsQuery.data.map((approval) => (
            <li key={approval.id}>
              <button
                type="button"
                onClick={() => setActiveApprovalId(approval.id)}
                className="flex w-full items-center justify-between gap-4 rounded-lg border border-border bg-card px-4 py-3 text-left transition-colors duration-fast hover:bg-lavender focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-text-primary">{approval.title}</p>
                  <p className="mt-0.5 text-xs text-text-secondary">
                    Requested by {approval.requested_by_email ?? 'system'} &middot; assigned to{' '}
                    {approval.assigned_role}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge
                    label={approval.risk_level}
                    className={RISK_CLASSES[approval.risk_level]}
                  />
                  <Badge label={approval.status} className={STATUS_CLASSES[approval.status]} />
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}

      <ApprovalDetailDialog
        workspaceId={workspaceId}
        approvalId={activeApprovalId}
        onClose={() => setActiveApprovalId(null)}
      />
    </div>
  );
}

function ApprovalDetailDialog({
  workspaceId,
  approvalId,
  onClose,
}: {
  workspaceId: string | undefined;
  approvalId: string | null;
  onClose: () => void;
}) {
  const approvalQuery = useApproval(workspaceId, approvalId ?? undefined);
  const decide = useDecideApproval(workspaceId, approvalId ?? undefined);
  const addComment = useAddApprovalComment(workspaceId, approvalId ?? undefined);

  const [pendingDecision, setPendingDecision] = useState<'approved' | 'rejected' | null>(null);
  const [reason, setReason] = useState('');
  const [commentBody, setCommentBody] = useState('');
  const [decisionError, setDecisionError] = useState<string | null>(null);

  const approval = approvalQuery.data;

  const handleConfirmDecision = () => {
    if (!pendingDecision) return;
    setDecisionError(null);
    decide.mutate(
      { status: pendingDecision, reason },
      {
        onSuccess: () => {
          setPendingDecision(null);
          setReason('');
        },
        onError: (error) => {
          setDecisionError(
            error instanceof ApiError ? error.message : 'Could not record this decision.',
          );
        },
      },
    );
  };

  return (
    <>
      <Dialog
        open={Boolean(approvalId)}
        onOpenChange={(open) => !open && onClose()}
        title={approval?.title ?? 'Approval request'}
        description={approval?.description || undefined}
        className="max-w-lg"
      >
        {approvalQuery.isPending && <Skeleton className="h-40 w-full rounded-lg" />}

        {approval && (
          <div className="flex flex-col gap-4">
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              <dt className="text-text-secondary">Risk</dt>
              <dd className="text-text-primary capitalize">{approval.risk_level}</dd>
              <dt className="text-text-secondary">Status</dt>
              <dd className="text-text-primary capitalize">{approval.status}</dd>
              <dt className="text-text-secondary">Assigned role</dt>
              <dd className="text-text-primary">{approval.assigned_role}</dd>
              <dt className="text-text-secondary">Requested by</dt>
              <dd className="text-text-primary">{approval.requested_by_email ?? 'system'}</dd>
              {approval.decided_by_email && (
                <>
                  <dt className="text-text-secondary">Decided by</dt>
                  <dd className="text-text-primary">{approval.decided_by_email}</dd>
                </>
              )}
            </dl>

            {approval.status === 'pending' && (
              <div className="flex flex-col gap-2 border-t border-border pt-4">
                <label
                  htmlFor="decision-reason"
                  className="text-xs font-medium text-text-secondary"
                >
                  Reason (optional, recorded as a comment)
                </label>
                <textarea
                  id="decision-reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  rows={2}
                  className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  placeholder="Why are you approving or rejecting this?"
                />
                {decisionError && <p className="text-xs text-status-failed">{decisionError}</p>}
                <div className="flex justify-end gap-2">
                  <Button variant="destructive" onClick={() => setPendingDecision('rejected')}>
                    Reject
                  </Button>
                  <Button variant="primary" onClick={() => setPendingDecision('approved')}>
                    Approve
                  </Button>
                </div>
              </div>
            )}

            <div className="border-t border-border pt-4">
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-medium text-text-secondary">
                <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
                Comments
              </h4>
              <ul className="flex flex-col gap-2">
                {approval.comments.length === 0 && (
                  <li className="text-xs text-text-muted">No comments yet.</li>
                )}
                {approval.comments.map((comment) => (
                  <li key={comment.id} className="rounded-md bg-lavender px-3 py-2 text-xs">
                    <p className="font-medium text-text-primary">
                      {comment.author_email ?? 'system'}
                    </p>
                    <p className="mt-0.5 text-text-secondary">{comment.body}</p>
                  </li>
                ))}
              </ul>
              <form
                className="mt-2 flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!commentBody.trim()) return;
                  addComment.mutate(commentBody, { onSuccess: () => setCommentBody('') });
                }}
              >
                <input
                  value={commentBody}
                  onChange={(e) => setCommentBody(e.target.value)}
                  placeholder="Add a comment…"
                  aria-label="Add a comment"
                  className="h-9 w-full rounded-md border border-border bg-card px-3 text-sm text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                />
                <Button
                  type="submit"
                  size="sm"
                  variant="secondary"
                  isLoading={addComment.isPending}
                >
                  Post
                </Button>
              </form>
            </div>
          </div>
        )}
      </Dialog>

      <ConfirmationDialog
        open={pendingDecision !== null}
        onOpenChange={(open) => !open && setPendingDecision(null)}
        title={pendingDecision === 'approved' ? 'Approve this request?' : 'Reject this request?'}
        description="This decision is recorded and cannot be reversed here."
        confirmLabel={pendingDecision === 'approved' ? 'Approve' : 'Reject'}
        isDestructive={pendingDecision === 'rejected'}
        isLoading={decide.isPending}
        onConfirm={handleConfirmDecision}
      />
    </>
  );
}
