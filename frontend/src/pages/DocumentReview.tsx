import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { useSession } from '@/features/auth/hooks';
import { useDocument } from '@/features/documents/hooks';
import { useCorrectField, useExtraction, useTransitionExtraction } from '@/features/extraction/hooks';
import type { ExtractedField } from '@/features/extraction/types';
import { ApiError } from '@/lib/apiClient';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Button } from '@/components/ui/Button';
import { FullPageSpinner } from '@/components/ui/FullPageSpinner';
import { ErrorState } from '@/components/ui/ErrorState';
import { ValidationAlert } from '@/components/extraction/ValidationAlert';
import { ExtractionFieldRow } from '@/components/extraction/ExtractionFieldRow';
import { ReviewActionBar } from '@/components/extraction/ReviewActionBar';
import { PDFViewer } from '@/components/extraction/PDFViewer';

const CAN_CORRECT_ROLES = new Set(['owner', 'admin', 'finance_manager', 'reviewer']);
const CAN_APPROVE_ROLES = new Set(['owner', 'admin', 'finance_manager']);

export function DocumentReviewPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const { data: session } = useSession();
  const workspaceId = session?.active_workspace_id ?? undefined;
  const role = session?.workspaces.find((w) => w.id === workspaceId)?.role;

  const documentQuery = useDocument(workspaceId, documentId);
  const extractionQuery = useExtraction(workspaceId, documentId);
  const correctField = useCorrectField(workspaceId, documentId);
  const transition = useTransitionExtraction(workspaceId, documentId);

  // Split view at lg+, tabbed below — decided in JS (not just CSS
  // `hidden`/`lg:hidden`) so only one layout is ever actually mounted.
  // Rendering both simultaneously would duplicate every field's input
  // (and its `id`/label association) in the DOM at once.
  const isSplitView = useMediaQuery('(min-width: 1024px)');

  const [selectedField, setSelectedField] = useState<ExtractedField | null>(null);
  const [dirtyFieldIds, setDirtyFieldIds] = useState<Set<string>>(new Set());
  const [conflict, setConflict] = useState(false);

  // Tab-close/refresh protection while a field edit is unsaved. Does not
  // cover in-app navigation via other AppShell links (this app uses a
  // plain BrowserRouter, not a data router with useBlocker support) —
  // see the phase completion report's known limitations.
  useEffect(() => {
    function handler(event: BeforeUnloadEvent) {
      if (dirtyFieldIds.size > 0) {
        event.preventDefault();
      }
    }
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirtyFieldIds]);

  const extraction = extractionQuery.data;
  const errorIssues = useMemo(() => extraction?.issues.filter((i) => i.severity === 'error') ?? [], [extraction]);

  function handleSelect(field: ExtractedField) {
    setSelectedField(field);
  }

  function handleDirtyChange(fieldId: string, isDirty: boolean) {
    setDirtyFieldIds((prev) => {
      const next = new Set(prev);
      if (isDirty) next.add(fieldId);
      else next.delete(fieldId);
      return next;
    });
  }

  function handleSave(field: ExtractedField, value: string) {
    if (!extraction) return;
    correctField.mutate(
      { fieldId: field.id, value, expected_version: extraction.version },
      {
        onSuccess: () => handleDirtyChange(field.id, false),
        onError: (err) => {
          if (err instanceof ApiError && err.code === 'stale_version') setConflict(true);
        },
      },
    );
  }

  function handleTransition(status: 'approved' | 'rejected' | 'pending_review') {
    if (!extraction) return;
    transition.mutate(
      { status, expected_version: extraction.version },
      {
        onError: (err) => {
          if (err instanceof ApiError && err.code === 'stale_version') setConflict(true);
        },
      },
    );
  }

  if (documentQuery.isLoading || extractionQuery.isLoading || !workspaceId) {
    return <FullPageSpinner />;
  }

  if (extractionQuery.isError) {
    return (
      <ErrorState
        title="No extraction found"
        description="This document has not been through structured extraction, or it isn't an invoice."
      />
    );
  }

  if (!extraction || !documentQuery.data) {
    return null;
  }

  const canCorrect = Boolean(role && CAN_CORRECT_ROLES.has(role)) && extraction.status === 'pending_review';
  const canApprove = Boolean(role && CAN_APPROVE_ROLES.has(role));
  const canReject = Boolean(role && CAN_CORRECT_ROLES.has(role));

  const fieldsPanel = (
    <div className="flex h-full flex-col gap-3 overflow-y-auto p-4">
      <ValidationAlert issues={extraction.issues} />
      {extraction.fields_data.map((field) => (
        <ExtractionFieldRow
          key={field.id}
          field={field}
          isSelected={selectedField?.id === field.id}
          isEditable={canCorrect}
          isSaving={correctField.isPending && correctField.variables?.fieldId === field.id}
          onSelect={handleSelect}
          onSave={handleSave}
          onDirtyChange={handleDirtyChange}
        />
      ))}
    </div>
  );

  const documentPanel = (
    <div className="h-full p-4">
      <PDFViewer
        fileUrl={documentQuery.data.download_url}
        highlight={
          selectedField?.bounding_box && selectedField.page_number
            ? { page: selectedField.page_number, box: selectedField.bounding_box }
            : null
        }
      />
    </div>
  );

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border bg-card px-4 py-3">
        <div className="flex items-center gap-3">
          <Link
            to="/app/review-queue"
            className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary"
          >
            <ArrowLeft className="size-4" /> Review Queue
          </Link>
          <h1 className="text-base font-semibold text-text-primary">{documentQuery.data.filename}</h1>
        </div>
      </div>

      {conflict && (
        <div className="flex items-center justify-between gap-2 border-b border-status-failed-bg bg-status-failed-bg px-4 py-2 text-sm text-status-failed">
          <span>This extraction was changed elsewhere. Reload to see the latest version before continuing.</span>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => {
              setConflict(false);
              void extractionQuery.refetch();
            }}
          >
            <RefreshCw className="mr-1 size-4" /> Reload
          </Button>
        </div>
      )}

      {/* Split view at lg+, tabbed below — reference layout preserved,
          responsiveness added per the phase's non-negotiable rule. */}
      {isSplitView ? (
        <div className="grid min-h-0 flex-1 grid-cols-2">
          <div className="min-h-0 border-r border-border">{documentPanel}</div>
          <div className="min-h-0">{fieldsPanel}</div>
        </div>
      ) : (
        <div className="min-h-0 flex-1">
          <Tabs defaultValue="fields" className="flex h-full flex-col">
            <TabsList className="mx-4 mt-3 w-fit">
              <TabsTrigger value="document">Document</TabsTrigger>
              <TabsTrigger value="fields">Fields</TabsTrigger>
            </TabsList>
            <TabsContent value="document" className="min-h-0 flex-1">
              {documentPanel}
            </TabsContent>
            <TabsContent value="fields" className="min-h-0 flex-1">
              {fieldsPanel}
            </TabsContent>
          </Tabs>
        </div>
      )}

      <ReviewActionBar
        status={extraction.status}
        canApprove={canApprove}
        canReject={canReject}
        isSubmitting={transition.isPending}
        blockedByErrors={errorIssues.length > 0}
        onApprove={() => handleTransition('approved')}
        onReject={() => handleTransition('rejected')}
        onRequestReview={() => handleTransition('pending_review')}
      />
    </div>
  );
}
