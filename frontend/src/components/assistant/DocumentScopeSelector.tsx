import type { DocumentSummary } from '@/features/documents/types';
import { cn } from '@/lib/utils';

export interface DocumentScopeSelectorProps {
  documents: DocumentSummary[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}

/** Lets the user narrow a new conversation to specific documents before
 * asking anything — an empty selection means "search every document in
 * the workspace" (see Conversation.document_scope on the backend). */
export function DocumentScopeSelector({ documents, selectedIds, onChange }: DocumentScopeSelectorProps) {
  function toggle(id: string) {
    onChange(selectedIds.includes(id) ? selectedIds.filter((x) => x !== id) : [...selectedIds, id]);
  }

  return (
    <fieldset className="space-y-1">
      <legend className="mb-1 text-xs font-medium text-text-secondary">
        Scope {selectedIds.length > 0 ? `(${selectedIds.length} selected)` : '(all documents)'}
      </legend>
      <div className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-border bg-card p-2">
        {documents.length === 0 && <p className="px-1 text-xs text-text-muted">No documents yet.</p>}
        {documents.map((doc) => (
          <label
            key={doc.id}
            className={cn(
              'flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 text-xs',
              selectedIds.includes(doc.id) ? 'bg-primary-soft text-primary' : 'text-text-secondary hover:bg-lavender',
            )}
          >
            <input
              type="checkbox"
              checked={selectedIds.includes(doc.id)}
              onChange={() => toggle(doc.id)}
              className="size-3.5 rounded border-border text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            />
            <span className="truncate">{doc.filename}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
