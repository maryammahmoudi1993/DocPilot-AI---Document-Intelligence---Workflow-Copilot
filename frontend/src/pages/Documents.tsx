import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Upload, Download, Archive, Trash2, FileStack } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { FilterBar } from '@/components/ui/FilterBar';
import { SearchInput } from '@/components/ui/SearchInput';
import { Select, type SelectOption } from '@/components/ui/Select';
import {
  DataTable,
  DataTableHead,
  DataTableBody,
  DataTableRow,
  DataTableCell,
  DataTableHeaderCell,
} from '@/components/ui/DataTable';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { IconButton } from '@/components/ui/IconButton';
import { ConfirmationDialog } from '@/components/ui/ConfirmationDialog';
import { useToast } from '@/components/ui/Toast';
import { DocumentStatusBadge } from '@/components/documents/DocumentStatusBadge';
import { BulkActionBar } from '@/components/documents/BulkActionBar';
import { UploadDialog } from '@/components/documents/UploadDialog';
import { useSession } from '@/features/auth/hooks';
import {
  useDocuments,
  useArchiveDocument,
  useDeleteDocument,
  useBulkArchiveDocuments,
  useBulkDeleteDocuments,
  useDownloadDocument,
  useDocumentUploadQueue,
} from '@/features/documents/hooks';
import type { DocumentOrdering, DocumentStatus, DocumentSummary } from '@/features/documents/types';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { ApiError } from '@/lib/apiClient';

const PAGE_SIZE = 20;

const STATUS_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'All statuses' },
  { value: 'uploaded', label: 'Uploaded' },
  { value: 'archived', label: 'Archived' },
];

const ORDERING_OPTIONS: SelectOption[] = [
  { value: '-created_at', label: 'Newest first' },
  { value: 'created_at', label: 'Oldest first' },
  { value: 'filename', label: 'Name (A–Z)' },
  { value: '-filename', label: 'Name (Z–A)' },
  { value: '-size_bytes', label: 'Largest first' },
  { value: 'size_bytes', label: 'Smallest first' },
];

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function ownerLabel(document: DocumentSummary): string {
  if (!document.uploaded_by) return '—';
  const { first_name, last_name } = document.uploaded_by;
  return [first_name, last_name].filter(Boolean).join(' ') || document.uploaded_by.email;
}

/**
 * Matches design-reference/ui/DocPilot AI - Documents.dc.html for
 * layout, spacing, and token language, reimplemented against the real
 * Phase 3 backend contract. The mock's confidence-score column and
 * "Needs Review"/"Processing"/"Failed" statuses belong to the later
 * AI-extraction pipeline and don't exist on `Document` yet (only
 * `uploaded`/`archived` do) — omitted here rather than faked. Likewise
 * the mock's "Assign reviewer"/"Start workflow" bulk actions and the
 * vendor/tags/date-range filter chips have no backing endpoint yet, so
 * only the real ones (search, status, sort, archive, delete) are wired
 * up.
 */
export function DocumentsPage() {
  const { data: session } = useSession();
  const workspaceId = session?.active_workspace_id ?? undefined;
  const { showToast } = useToast();

  const [searchParams, setSearchParams] = useSearchParams();
  const search = searchParams.get('search') ?? '';
  const status = (searchParams.get('status') as DocumentStatus | null) ?? undefined;
  const ordering = (searchParams.get('ordering') as DocumentOrdering | null) ?? '-created_at';
  const page = Number(searchParams.get('page') ?? '1');

  const [searchInput, setSearchInput] = useState(search);
  const debouncedSearch = useDebouncedValue(searchInput, 400);

  useEffect(() => {
    setSearchParams((prev) => {
      const current = prev.get('search') ?? '';
      if (current === debouncedSearch) return prev;
      const next = new URLSearchParams(prev);
      if (debouncedSearch) next.set('search', debouncedSearch);
      else next.delete('search');
      next.delete('page');
      return next;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch]);

  const setFilter = (key: string, value: string | undefined) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value);
      else next.delete(key);
      next.delete('page');
      return next;
    });
  };

  const listParams = { search: search || undefined, status, ordering, page, page_size: PAGE_SIZE };
  const { data, isLoading, isError, refetch } = useDocuments(workspaceId, listParams);
  // TanStack Query v5's `isLoading` is false for a disabled query (no
  // workspace resolved yet), which would otherwise flash the empty state
  // before the session/workspace has even loaded.
  const showLoading = isLoading || !workspaceId;

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  // Selection only makes sense for the currently visible page/filter —
  // reset it during render when the filter set changes, rather than in a
  // useEffect (React's recommended pattern for adjusting state in
  // response to prop/derived-value changes; avoids an extra render pass).
  const filterSignature = `${search}|${status ?? ''}|${ordering}|${page}`;
  const [lastFilterSignature, setLastFilterSignature] = useState(filterSignature);
  if (filterSignature !== lastFilterSignature) {
    setLastFilterSignature(filterSignature);
    setSelectedIds(new Set());
  }

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const uploadQueue = useDocumentUploadQueue(workspaceId);

  const [bulkConfirm, setBulkConfirm] = useState<'archive' | 'delete' | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DocumentSummary | null>(null);

  const archiveDocument = useArchiveDocument(workspaceId);
  const deleteDocument = useDeleteDocument(workspaceId);
  const bulkArchive = useBulkArchiveDocuments(workspaceId);
  const bulkDelete = useBulkDeleteDocuments(workspaceId);
  const downloadDocument = useDownloadDocument(workspaceId);

  const documents = data?.results ?? [];
  const selectedCount = selectedIds.size;
  const allSelected = documents.length > 0 && selectedIds.size === documents.length;

  const toggleSelectAll = (checked: boolean) => {
    setSelectedIds(checked ? new Set(documents.map((doc) => doc.id)) : new Set());
  };

  const toggleSelect = (id: string, checked: boolean) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const handleErrorToast = (error: unknown, fallback: string) => {
    showToast({
      variant: 'error',
      title: error instanceof ApiError ? error.message : fallback,
    });
  };

  const confirmBulkAction = () => {
    const ids = Array.from(selectedIds);
    if (bulkConfirm === 'archive') {
      bulkArchive.mutate(ids, {
        onSuccess: () => {
          showToast({ variant: 'success', title: `${ids.length} document(s) archived.` });
          setSelectedIds(new Set());
          setBulkConfirm(null);
        },
        onError: (error) => handleErrorToast(error, 'Could not archive the selected documents.'),
      });
    } else if (bulkConfirm === 'delete') {
      bulkDelete.mutate(ids, {
        onSuccess: () => {
          showToast({ variant: 'success', title: `${ids.length} document(s) deleted.` });
          setSelectedIds(new Set());
          setBulkConfirm(null);
        },
        onError: (error) => handleErrorToast(error, 'Could not delete the selected documents.'),
      });
    }
  };

  const confirmRowDelete = () => {
    if (!deleteTarget) return;
    deleteDocument.mutate(deleteTarget.id, {
      onSuccess: () => {
        showToast({ variant: 'success', title: `${deleteTarget.filename} deleted.` });
        setDeleteTarget(null);
      },
      onError: (error) => {
        handleErrorToast(error, 'Could not delete the document.');
        setDeleteTarget(null);
      },
    });
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title="Documents"
        description="Manage, search, filter, and organize all uploaded files."
        actions={
          <Button onClick={() => setIsUploadOpen(true)}>
            <Upload className="h-4 w-4" aria-hidden="true" />
            Upload Document
          </Button>
        }
      />

      <FilterBar>
        <div className="flex-1">
          <SearchInput
            aria-label="Search documents"
            placeholder="Search files..."
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />
        </div>
        <div className="w-40">
          <Select
            aria-label="Status"
            options={STATUS_OPTIONS}
            value={status ?? 'all'}
            onValueChange={(value) => setFilter('status', value === 'all' ? undefined : value)}
          />
        </div>
        <div className="w-44">
          <Select
            aria-label="Sort by"
            options={ORDERING_OPTIONS}
            value={ordering}
            onValueChange={(value) => setFilter('ordering', value)}
          />
        </div>
      </FilterBar>

      <BulkActionBar
        selectedCount={selectedCount}
        onArchive={() => setBulkConfirm('archive')}
        onDelete={() => setBulkConfirm('delete')}
        isBusy={bulkArchive.isPending || bulkDelete.isPending}
      />

      {showLoading ? (
        <div role="status" aria-label="Loading documents" className="space-y-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState
          title="Couldn't load documents"
          description="Please try again. If the problem continues, contact support."
          onRetry={() => void refetch()}
        />
      ) : documents.length === 0 ? (
        <EmptyState
          icon={FileStack}
          title="No documents yet"
          description="Upload invoices, contracts, receipts, or reports to get started in this demo workspace."
          action={<Button onClick={() => setIsUploadOpen(true)}>Upload Document</Button>}
        />
      ) : (
        <>
          <DataTable caption="Documents">
            <DataTableHead>
              <tr>
                <DataTableHeaderCell>
                  <input
                    type="checkbox"
                    aria-label="Select all documents"
                    checked={allSelected}
                    onChange={(event) => toggleSelectAll(event.target.checked)}
                  />
                </DataTableHeaderCell>
                <DataTableHeaderCell>Name</DataTableHeaderCell>
                <DataTableHeaderCell>Size</DataTableHeaderCell>
                <DataTableHeaderCell>Status</DataTableHeaderCell>
                <DataTableHeaderCell>Uploaded on</DataTableHeaderCell>
                <DataTableHeaderCell>Owner</DataTableHeaderCell>
                <DataTableHeaderCell>
                  <span className="sr-only">Actions</span>
                </DataTableHeaderCell>
              </tr>
            </DataTableHead>
            <DataTableBody>
              {documents.map((document) => (
                <DataTableRow key={document.id}>
                  <DataTableCell>
                    <input
                      type="checkbox"
                      aria-label={`Select ${document.filename}`}
                      checked={selectedIds.has(document.id)}
                      onChange={(event) => toggleSelect(document.id, event.target.checked)}
                    />
                  </DataTableCell>
                  <DataTableCell className="max-w-xs truncate font-medium">{document.filename}</DataTableCell>
                  <DataTableCell>{formatSize(document.size_bytes)}</DataTableCell>
                  <DataTableCell>
                    <DocumentStatusBadge status={document.status} />
                  </DataTableCell>
                  <DataTableCell>{formatDate(document.created_at)}</DataTableCell>
                  <DataTableCell>{ownerLabel(document)}</DataTableCell>
                  <DataTableCell>
                    <div className="flex items-center justify-end gap-1">
                      <IconButton
                        aria-label={`Download ${document.filename}`}
                        onClick={() => downloadDocument.mutate(document.id)}
                        disabled={downloadDocument.isPending}
                        className="h-8 w-8"
                      >
                        <Download className="h-3.5 w-3.5" aria-hidden="true" />
                      </IconButton>
                      {document.status === 'uploaded' && (
                        <IconButton
                          aria-label={`Archive ${document.filename}`}
                          onClick={() =>
                            archiveDocument.mutate(document.id, {
                              onError: (error) => handleErrorToast(error, 'Could not archive the document.'),
                            })
                          }
                          disabled={archiveDocument.isPending}
                          className="h-8 w-8"
                        >
                          <Archive className="h-3.5 w-3.5" aria-hidden="true" />
                        </IconButton>
                      )}
                      <IconButton
                        aria-label={`Delete ${document.filename}`}
                        onClick={() => setDeleteTarget(document)}
                        className="h-8 w-8"
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                      </IconButton>
                    </div>
                  </DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>

          <div className="flex items-center justify-between text-sm text-text-secondary">
            <span>{data?.count ?? 0} total</span>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={!data?.previous}
                onClick={() => setFilter('page', String(page - 1))}
              >
                Previous
              </Button>
              <span>
                Page {page} of {Math.max(1, Math.ceil((data?.count ?? 0) / PAGE_SIZE))}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={!data?.next}
                onClick={() => setFilter('page', String(page + 1))}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}

      <UploadDialog
        open={isUploadOpen}
        onOpenChange={setIsUploadOpen}
        items={uploadQueue.items}
        onFilesSelected={uploadQueue.addFiles}
        onCancel={uploadQueue.cancel}
        onRetry={uploadQueue.retry}
        onRemove={uploadQueue.remove}
        workspaceId={workspaceId}
      />

      <ConfirmationDialog
        open={bulkConfirm !== null}
        onOpenChange={(open) => !open && setBulkConfirm(null)}
        title={bulkConfirm === 'archive' ? 'Archive selected documents?' : 'Delete selected documents?'}
        description={
          bulkConfirm === 'archive'
            ? `${selectedCount} document(s) will be moved to Archived.`
            : `${selectedCount} document(s) will be permanently deleted. This cannot be undone.`
        }
        confirmLabel={bulkConfirm === 'archive' ? 'Confirm' : 'Delete'}
        isDestructive={bulkConfirm === 'delete'}
        isLoading={bulkArchive.isPending || bulkDelete.isPending}
        onConfirm={confirmBulkAction}
      />

      <ConfirmationDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete document?"
        description={
          deleteTarget ? `"${deleteTarget.filename}" will be permanently deleted. This cannot be undone.` : undefined
        }
        confirmLabel="Delete"
        isDestructive
        isLoading={deleteDocument.isPending}
        onConfirm={confirmRowDelete}
      />
    </div>
  );
}
