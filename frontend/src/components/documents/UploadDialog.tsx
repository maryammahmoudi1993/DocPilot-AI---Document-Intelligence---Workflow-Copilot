import { CheckCircle2, FileWarning, X } from 'lucide-react';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { IconButton } from '@/components/ui/IconButton';
import { ProcessingStatusInline } from '@/components/processing/ProcessingStatusInline';
import { UploadDropzone } from './UploadDropzone';
import type { UploadQueueItem } from '@/features/documents/hooks';

export interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: UploadQueueItem[];
  onFilesSelected: (files: File[]) => void;
  onCancel: (id: string) => void;
  onRetry: (id: string) => void;
  onRemove: (id: string) => void;
  /** Needed to track each successfully-uploaded file's async processing
   * job (see ProcessingStatusInline) — undefined only very briefly
   * while the session/workspace is still loading. */
  workspaceId: string | undefined;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadDialog({
  open,
  onOpenChange,
  items,
  onFilesSelected,
  onCancel,
  onRetry,
  onRemove,
  workspaceId,
}: UploadDialogProps) {
  const anyUploading = items.some((item) => item.status === 'uploading');

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        // Uploads keep running via their own AbortController even if the
        // dialog is closed mid-flight; closing only hides the UI.
        onOpenChange(next);
      }}
      title="Upload documents"
      description="PDF, PNG, JPG, DOCX, XLSX, CSV, or TXT files up to 20MB."
    >
      <div className="space-y-4">
        <UploadDropzone onFilesSelected={onFilesSelected} />

        {items.length > 0 && (
          <ul className="max-h-64 space-y-2 overflow-y-auto" aria-label="Upload progress">
            {items.map((item) => (
              <li
                key={item.id}
                className="rounded-md border border-border bg-card p-3 text-sm"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="min-w-0 flex-1 truncate font-medium text-text-primary">{item.file.name}</span>
                  <span className="shrink-0 text-xs text-text-muted">{formatSize(item.file.size)}</span>
                  {item.status === 'uploading' && (
                    <IconButton
                      aria-label={`Cancel upload of ${item.file.name}`}
                      onClick={() => onCancel(item.id)}
                      className="h-7 w-7"
                    >
                      <X className="h-3.5 w-3.5" aria-hidden="true" />
                    </IconButton>
                  )}
                  {item.status === 'success' && (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-status-approved">
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                      Uploaded
                    </span>
                  )}
                </div>

                {item.status === 'uploading' && (
                  <div
                    role="progressbar"
                    aria-label={`Upload progress for ${item.file.name}`}
                    aria-valuenow={item.progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-lavender"
                  >
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-fast"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                )}

                {item.status === 'error' && (
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <p className="flex items-center gap-1.5 text-xs text-status-failed">
                      <FileWarning className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                      {item.error}
                    </p>
                    <div className="flex shrink-0 gap-1">
                      <Button
                        variant="secondary"
                        size="sm"
                        aria-label={`Retry upload of ${item.file.name}`}
                        onClick={() => onRetry(item.id)}
                      >
                        Retry
                      </Button>
                      <IconButton aria-label={`Remove ${item.file.name} from upload list`} onClick={() => onRemove(item.id)}>
                        <X className="h-3.5 w-3.5" aria-hidden="true" />
                      </IconButton>
                    </div>
                  </div>
                )}

                {item.status === 'success' && item.documentId && (
                  <ProcessingStatusInline workspaceId={workspaceId} documentId={item.documentId} />
                )}
              </li>
            ))}
          </ul>
        )}

        <div className="flex justify-end">
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={anyUploading}>
            {anyUploading ? 'Uploading…' : 'Done'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
