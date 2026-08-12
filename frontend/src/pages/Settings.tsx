import { useState } from 'react';
import { useSession } from '@/features/auth/hooks';
import { useUpdateWorkspaceSettings, useWorkspaceSettings } from '@/features/workspaceSettings/hooks';
import type { WorkspaceSettingsUpdate } from '@/features/workspaceSettings/types';
import { ApiError } from '@/lib/apiClient';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useToast } from '@/components/ui/Toast';

function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-4 py-3">
      <span>
        <span className="block text-sm font-medium text-text-primary">{label}</span>
        {description && <span className="block text-xs text-text-secondary">{description}</span>}
      </span>
      <input
        type="checkbox"
        role="switch"
        aria-checked={checked}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-5 w-9 shrink-0 accent-primary"
      />
    </label>
  );
}

export function SettingsPage() {
  const { data: session } = useSession();
  const workspaceId = session?.active_workspace_id ?? undefined;

  const settingsQuery = useWorkspaceSettings(workspaceId);
  const updateSettings = useUpdateWorkspaceSettings(workspaceId);
  const { showToast } = useToast();

  const [form, setForm] = useState<WorkspaceSettingsUpdate | null>(null);
  const [retentionError, setRetentionError] = useState<string | null>(null);

  // Loads the editable form the moment settings first arrive, adjusted
  // during render (React's documented pattern for syncing state from a
  // prop/query, rather than a useEffect + setState round trip) — synced
  // once per `updated_at` so a background refetch after save doesn't
  // clobber the form the user is still editing.
  const [syncedUpdatedAt, setSyncedUpdatedAt] = useState<string | null>(null);
  if (settingsQuery.data && syncedUpdatedAt !== settingsQuery.data.updated_at) {
    setSyncedUpdatedAt(settingsQuery.data.updated_at);
    setForm({
      notify_on_approval_requested: settingsQuery.data.notify_on_approval_requested,
      notify_on_document_processed: settingsQuery.data.notify_on_document_processed,
      webhook_notifications_enabled: settingsQuery.data.webhook_notifications_enabled,
      auto_classify_enabled: settingsQuery.data.auto_classify_enabled,
      document_retention_days: settingsQuery.data.document_retention_days,
      raw_text_retention_days: settingsQuery.data.raw_text_retention_days,
    });
  }

  if (settingsQuery.isPending) {
    return <Skeleton className="h-96 w-full max-w-xl rounded-lg" />;
  }

  if (settingsQuery.isError || !form) {
    return <ErrorState description="Could not load workspace settings." onRetry={() => settingsQuery.refetch()} />;
  }

  const parseRetention = (value: string): number | null | undefined => {
    if (value.trim() === '') return null;
    const parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed < 1) return undefined;
    return parsed;
  };

  const handleSave = () => {
    setRetentionError(null);
    updateSettings.mutate(form, {
      onSuccess: () => showToast({ variant: 'success', title: 'Settings saved' }),
      onError: (error) => {
        showToast({
          variant: 'error',
          title: "Couldn't save settings",
          description: error instanceof ApiError ? error.message : 'Please try again.',
        });
      },
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Settings" description="Manage workspace notification, processing, and retention preferences." />

      <div className="max-w-xl rounded-lg border border-border bg-card p-6">
        <h2 className="mb-1 text-base font-semibold text-text-primary">Notifications</h2>
        <p className="mb-2 text-xs text-text-secondary">
          Controls in-app and webhook notifications for this workspace.
        </p>
        <div className="divide-y divide-divider">
          <Toggle
            label="Notify on approval requested"
            checked={form.notify_on_approval_requested ?? true}
            onChange={(checked) => setForm({ ...form, notify_on_approval_requested: checked })}
          />
          <Toggle
            label="Notify on document processed"
            checked={form.notify_on_document_processed ?? true}
            onChange={(checked) => setForm({ ...form, notify_on_document_processed: checked })}
          />
          <Toggle
            label="Webhook notifications enabled"
            checked={form.webhook_notifications_enabled ?? true}
            onChange={(checked) => setForm({ ...form, webhook_notifications_enabled: checked })}
          />
        </div>

        <h2 className="mb-1 mt-6 text-base font-semibold text-text-primary">Processing rules</h2>
        <div className="divide-y divide-divider">
          <Toggle
            label="Auto-classify uploaded documents"
            description="When off, new documents are left unclassified for manual review."
            checked={form.auto_classify_enabled ?? true}
            onChange={(checked) => setForm({ ...form, auto_classify_enabled: checked })}
          />
        </div>

        <h2 className="mb-1 mt-6 text-base font-semibold text-text-primary">Data retention</h2>
        <p className="mb-3 text-xs text-text-secondary">
          Leave blank to keep data indefinitely.
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="document-retention" className="mb-1 block text-xs font-medium text-text-secondary">
              Document retention (days)
            </label>
            <Input
              id="document-retention"
              type="number"
              min={1}
              value={form.document_retention_days ?? ''}
              onChange={(e) => {
                const parsed = parseRetention(e.target.value);
                if (parsed === undefined) {
                  setRetentionError('Retention must be at least 1 day, or blank.');
                  return;
                }
                setRetentionError(null);
                setForm({ ...form, document_retention_days: parsed });
              }}
            />
          </div>
          <div>
            <label htmlFor="raw-text-retention" className="mb-1 block text-xs font-medium text-text-secondary">
              Raw text retention (days)
            </label>
            <Input
              id="raw-text-retention"
              type="number"
              min={1}
              value={form.raw_text_retention_days ?? ''}
              onChange={(e) => {
                const parsed = parseRetention(e.target.value);
                if (parsed === undefined) {
                  setRetentionError('Retention must be at least 1 day, or blank.');
                  return;
                }
                setRetentionError(null);
                setForm({ ...form, raw_text_retention_days: parsed });
              }}
            />
          </div>
        </div>
        {retentionError && <p className="mt-2 text-xs text-status-failed">{retentionError}</p>}

        <div className="mt-6 flex justify-end border-t border-border pt-4">
          <Button onClick={handleSave} isLoading={updateSettings.isPending} disabled={Boolean(retentionError)}>
            Save changes
          </Button>
        </div>
      </div>
    </div>
  );
}
