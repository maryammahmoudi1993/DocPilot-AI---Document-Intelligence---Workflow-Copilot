import { useState } from 'react';
import { Plug, Plus, Trash2 } from 'lucide-react';
import { useSession } from '@/features/auth/hooks';
import { MANAGER_ROLES } from '@/features/auth/types';
import {
  useCreateWebhookEndpoint,
  useDeleteWebhookEndpoint,
  useWebhookDeliveries,
  useWebhookEndpoints,
} from '@/features/notifications/hooks';
import { ApiError } from '@/lib/apiClient';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Dialog } from '@/components/ui/Dialog';
import { ConfirmationDialog } from '@/components/ui/ConfirmationDialog';
import { IconButton } from '@/components/ui/IconButton';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { cn } from '@/lib/utils';

export function IntegrationsPage() {
  const { data: session } = useSession();
  const workspaceId = session?.active_workspace_id ?? undefined;
  const role = session?.workspaces.find((w) => w.id === workspaceId)?.role;
  const canManage = Boolean(role && MANAGER_ROLES.includes(role));

  const endpointsQuery = useWebhookEndpoints(workspaceId);
  const createEndpoint = useCreateWebhookEndpoint(workspaceId);
  const deleteEndpoint = useDeleteWebhookEndpoint(workspaceId);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [secret, setSecret] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deliveriesEndpointId, setDeliveriesEndpointId] = useState<string | null>(null);

  const resetCreateForm = () => {
    setName('');
    setUrl('');
    setSecret('');
    setCreateError(null);
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    createEndpoint.mutate(
      { name, url, secret },
      {
        onSuccess: () => {
          setIsCreateOpen(false);
          resetCreateForm();
        },
        onError: (error) => {
          setCreateError(
            error instanceof ApiError ? error.message : 'Could not create the endpoint.',
          );
        },
      },
    );
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Integrations"
        description="Simulated webhook integrations — deliveries are real HTTP calls signed with a per-endpoint secret, but this is a portfolio demo, not a verified third-party integration."
        actions={
          canManage && (
            <Button onClick={() => setIsCreateOpen(true)}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              New endpoint
            </Button>
          )
        }
      />

      {endpointsQuery.isPending && (
        <div className="flex flex-col gap-2">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      )}

      {endpointsQuery.isError && (
        <ErrorState
          description="Could not load webhook endpoints."
          onRetry={() => endpointsQuery.refetch()}
        />
      )}

      {endpointsQuery.data && endpointsQuery.data.length === 0 && (
        <EmptyState
          icon={Plug}
          title="No integrations configured"
          description="Add a webhook endpoint to receive events from documents, approvals, and workflows."
        />
      )}

      {endpointsQuery.data && endpointsQuery.data.length > 0 && (
        <ul className="flex flex-col gap-2">
          {endpointsQuery.data.map((endpoint) => (
            <li
              key={endpoint.id}
              className="flex items-center justify-between gap-4 rounded-lg border border-border bg-card px-4 py-3"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-medium text-text-primary">{endpoint.name}</p>
                  <span className="inline-flex items-center rounded-full bg-lavender px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-text-secondary">
                    Simulated integration
                  </span>
                  <span
                    className={cn(
                      'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium',
                      endpoint.is_active
                        ? 'bg-status-approved-bg text-status-approved'
                        : 'bg-lavender text-text-secondary',
                    )}
                  >
                    {endpoint.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <p className="mt-0.5 truncate text-xs text-text-secondary">{endpoint.url}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setDeliveriesEndpointId(endpoint.id)}
                >
                  Deliveries
                </Button>
                {canManage && (
                  <IconButton
                    aria-label={`Delete ${endpoint.name}`}
                    onClick={() => setDeletingId(endpoint.id)}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </IconButton>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      <Dialog
        open={isCreateOpen}
        onOpenChange={(open) => {
          setIsCreateOpen(open);
          if (!open) resetCreateForm();
        }}
        title="New webhook endpoint"
        description="Events will be signed with HMAC-SHA256 using the secret below (X-DocPilot-Signature header)."
      >
        <form onSubmit={handleCreate} className="flex flex-col gap-3">
          <div>
            <label
              htmlFor="endpoint-name"
              className="mb-1 block text-xs font-medium text-text-secondary"
            >
              Name
            </label>
            <Input
              id="endpoint-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div>
            <label
              htmlFor="endpoint-url"
              className="mb-1 block text-xs font-medium text-text-secondary"
            >
              URL
            </label>
            <Input
              id="endpoint-url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/webhooks/docpilot"
              required
            />
          </div>
          <div>
            <label
              htmlFor="endpoint-secret"
              className="mb-1 block text-xs font-medium text-text-secondary"
            >
              Secret (min 8 characters)
            </label>
            <Input
              id="endpoint-secret"
              type="password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              minLength={8}
              required
            />
          </div>
          {createError && <p className="text-xs text-status-failed">{createError}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createEndpoint.isPending}>
              Create
            </Button>
          </div>
        </form>
      </Dialog>

      <ConfirmationDialog
        open={deletingId !== null}
        onOpenChange={(open) => !open && setDeletingId(null)}
        title="Delete this endpoint?"
        description="Future events will no longer be delivered to this URL. This cannot be undone."
        confirmLabel="Delete"
        isDestructive
        isLoading={deleteEndpoint.isPending}
        onConfirm={() => {
          if (!deletingId) return;
          deleteEndpoint.mutate(deletingId, { onSuccess: () => setDeletingId(null) });
        }}
      />

      <DeliveriesDialog
        workspaceId={workspaceId}
        endpointId={deliveriesEndpointId}
        onClose={() => setDeliveriesEndpointId(null)}
      />
    </div>
  );
}

function DeliveriesDialog({
  workspaceId,
  endpointId,
  onClose,
}: {
  workspaceId: string | undefined;
  endpointId: string | null;
  onClose: () => void;
}) {
  const deliveriesQuery = useWebhookDeliveries(workspaceId, endpointId ?? undefined);

  return (
    <Dialog
      open={Boolean(endpointId)}
      onOpenChange={(open) => !open && onClose()}
      title="Delivery log"
      className="max-w-lg"
    >
      {deliveriesQuery.isPending && <Skeleton className="h-32 w-full rounded-lg" />}
      {deliveriesQuery.data && deliveriesQuery.data.length === 0 && (
        <p className="text-sm text-text-secondary">No deliveries yet.</p>
      )}
      {deliveriesQuery.data && deliveriesQuery.data.length > 0 && (
        <ul className="flex max-h-80 flex-col gap-2 overflow-y-auto">
          {deliveriesQuery.data.map((delivery) => (
            <li key={delivery.id} className="rounded-md bg-lavender px-3 py-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-medium text-text-primary">{delivery.event_type}</span>
                <span
                  className={cn(
                    'rounded-full px-2 py-0.5 text-[10px] font-medium capitalize',
                    delivery.status === 'succeeded' && 'bg-status-approved-bg text-status-approved',
                    delivery.status === 'failed' && 'bg-status-failed-bg text-status-failed',
                    delivery.status === 'pending' &&
                      'bg-status-processing-bg text-status-processing',
                  )}
                >
                  {delivery.status}
                </span>
              </div>
              <p className="mt-1 text-text-secondary">
                Attempt {delivery.attempt_count}
                {delivery.response_status_code ? ` · HTTP ${delivery.response_status_code}` : ''}
                {delivery.error_code ? ` · ${delivery.error_code}` : ''}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Dialog>
  );
}
