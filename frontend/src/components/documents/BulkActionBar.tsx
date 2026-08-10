import { Archive, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export interface BulkActionBarProps {
  selectedCount: number;
  onArchive: () => void;
  onDelete: () => void;
  isBusy?: boolean;
}

export function BulkActionBar({ selectedCount, onArchive, onDelete, isBusy = false }: BulkActionBarProps) {
  if (selectedCount === 0) return null;

  return (
    <div className="flex items-center justify-between gap-3 rounded-lg bg-lavender px-4 py-2.5">
      <span className="text-sm font-medium text-primary">
        {selectedCount} {selectedCount === 1 ? 'document' : 'documents'} selected
      </span>
      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm" onClick={onArchive} disabled={isBusy}>
          <Archive className="h-3.5 w-3.5" aria-hidden="true" />
          Archive
        </Button>
        <Button variant="destructive" size="sm" onClick={onDelete} disabled={isBusy}>
          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
          Delete
        </Button>
      </div>
    </div>
  );
}
