import { X } from 'lucide-react';
import { useDocument } from '@/features/documents/hooks';
import { IconButton } from '@/components/ui/IconButton';
import { FullPageSpinner } from '@/components/ui/FullPageSpinner';
import { ErrorState } from '@/components/ui/ErrorState';
import { PDFViewer } from '@/components/extraction/PDFViewer';

export interface SourcePanelProps {
  workspaceId: string | undefined;
  documentId: string;
  page: number;
  onClose: () => void;
}

/** Opens the cited document at the cited page — the "citation opens
 * correct document and page" behavior. Bounding-box highlighting reuses
 * PDFViewer's existing `highlight` prop; this app's citations don't
 * carry coordinates yet (see apps.assistant.models.AnswerCitation), so
 * it's page-level only for now, same documented gap as the extraction
 * review PDF viewer. */
export function SourcePanel({ workspaceId, documentId, page, onClose }: SourcePanelProps) {
  const { data: document, isLoading, isError } = useDocument(workspaceId, documentId);

  return (
    <div className="flex h-full flex-col border-l border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-text-primary">Source</h2>
        <IconButton aria-label="Close source panel" onClick={onClose}>
          <X className="size-4" />
        </IconButton>
      </div>
      <div className="min-h-0 flex-1 p-3">
        {isLoading && <FullPageSpinner />}
        {isError && <ErrorState title="Couldn't load this document" />}
        {document && <PDFViewer fileUrl={document.download_url} highlight={{ page }} />}
      </div>
    </div>
  );
}
