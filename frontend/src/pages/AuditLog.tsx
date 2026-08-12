import { useState } from 'react';
import { ChevronDown, ChevronRight, History } from 'lucide-react';
import { useSession } from '@/features/auth/hooks';
import { useAuditEvents } from '@/features/audit/hooks';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';

export function AuditLogPage() {
  const { data: session } = useSession();
  const workspaceId = session?.active_workspace_id ?? undefined;

  const [eventType, setEventType] = useState('');
  const [since, setSince] = useState('');
  const [until, setUntil] = useState('');
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const eventsQuery = useAuditEvents(workspaceId, {
    event_type: eventType || undefined,
    since: since ? new Date(since).toISOString() : undefined,
    until: until ? new Date(until).toISOString() : undefined,
    page,
  });

  const events = eventsQuery.data?.results ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Audit Log"
        description="Immutable record of workspace activity — nothing here can be edited or deleted through the app."
      />

      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label
            htmlFor="audit-event-type"
            className="mb-1 block text-xs font-medium text-text-secondary"
          >
            Event type
          </label>
          <Input
            id="audit-event-type"
            value={eventType}
            onChange={(e) => {
              setEventType(e.target.value);
              setPage(1);
            }}
            placeholder="e.g. approval.approved"
            className="w-56"
          />
        </div>
        <div>
          <label
            htmlFor="audit-since"
            className="mb-1 block text-xs font-medium text-text-secondary"
          >
            Since
          </label>
          <Input
            id="audit-since"
            type="date"
            value={since}
            onChange={(e) => {
              setSince(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div>
          <label
            htmlFor="audit-until"
            className="mb-1 block text-xs font-medium text-text-secondary"
          >
            Until
          </label>
          <Input
            id="audit-until"
            type="date"
            value={until}
            onChange={(e) => {
              setUntil(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      {eventsQuery.isPending && (
        <div className="flex flex-col gap-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      )}

      {eventsQuery.isError && (
        <ErrorState
          description="Could not load the audit log."
          onRetry={() => eventsQuery.refetch()}
        />
      )}

      {eventsQuery.data && events.length === 0 && (
        <EmptyState
          icon={History}
          title="No events found"
          description="Try widening the date range or clearing filters."
        />
      )}

      {events.length > 0 && (
        <ul className="flex flex-col gap-1">
          {events.map((event) => {
            const isExpanded = expandedId === event.id;
            const hasMetadata = Object.keys(event.metadata).length > 0;
            return (
              <li key={event.id} className="rounded-lg border border-border bg-card">
                <button
                  type="button"
                  onClick={() => hasMetadata && setExpandedId(isExpanded ? null : event.id)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  aria-expanded={hasMetadata ? isExpanded : undefined}
                >
                  {hasMetadata ? (
                    isExpanded ? (
                      <ChevronDown
                        className="h-4 w-4 shrink-0 text-text-muted"
                        aria-hidden="true"
                      />
                    ) : (
                      <ChevronRight
                        className="h-4 w-4 shrink-0 text-text-muted"
                        aria-hidden="true"
                      />
                    )
                  ) : (
                    <span className="w-4 shrink-0" />
                  )}
                  <span className="min-w-0 flex-1">
                    <span className="block font-mono text-sm text-text-primary">
                      {event.event_type}
                    </span>
                    <span className="block text-xs text-text-secondary">
                      {event.actor_email ?? 'system'} &middot;{' '}
                      {new Date(event.created_at).toLocaleString()}
                    </span>
                  </span>
                </button>
                {isExpanded && hasMetadata && (
                  <pre className="overflow-x-auto rounded-b-lg bg-lavender px-4 py-3 text-xs text-text-secondary">
                    {JSON.stringify(event.metadata, null, 2)}
                  </pre>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {eventsQuery.data && (eventsQuery.data.next || eventsQuery.data.previous) && (
        <div className="flex justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            disabled={!eventsQuery.data.previous}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={!eventsQuery.data.next}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
