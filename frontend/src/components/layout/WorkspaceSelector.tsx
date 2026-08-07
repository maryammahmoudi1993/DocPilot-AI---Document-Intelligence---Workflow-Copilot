import { useSession, useSetActiveWorkspace } from '@/features/auth/hooks';
import { Select } from '@/components/ui/Select';
import { Skeleton } from '@/components/ui/Skeleton';
import { useToast } from '@/components/ui/Toast';

/** Loading/empty/error states are all real, not decorative — the
 * workspace list is a live query, not static config. */
export function WorkspaceSelector() {
  const { data, isLoading, isError } = useSession();
  const setActiveWorkspace = useSetActiveWorkspace();
  const { showToast } = useToast();

  if (isLoading) {
    return <Skeleton className="h-9 w-40" />;
  }

  if (isError) {
    return <span className="text-xs text-status-failed">Couldn't load workspaces</span>;
  }

  if (!data || data.workspaces.length === 0) {
    return <span className="text-xs text-text-muted">No workspaces</span>;
  }

  return (
    <Select
      aria-label="Active workspace"
      value={data.active_workspace_id ?? undefined}
      options={data.workspaces.map((workspace) => ({ value: workspace.id, label: workspace.name }))}
      onValueChange={(workspaceId) => {
        setActiveWorkspace.mutate(workspaceId, {
          onError: () => {
            // The Select stays bound to the query's current value, so a
            // failed switch has nothing to visually roll back — the
            // toast is the recovery signal.
            showToast({
              variant: 'error',
              title: "Couldn't switch workspace",
              description: 'Please try again.',
            });
          },
        });
      }}
      className="w-40"
    />
  );
}
