import { useMemo, useRef, useState } from 'react';
import { Send, Sparkles, Square } from 'lucide-react';
import { useSession } from '@/features/auth/hooks';
import { useDocuments } from '@/features/documents/hooks';
import {
  useAskQuestion,
  useConversation,
  useConversations,
  useCreateConversation,
} from '@/features/assistant/hooks';
import type { AnswerCitation } from '@/features/assistant/types';
import { ApiError } from '@/lib/apiClient';
import { Button } from '@/components/ui/Button';
import { FullPageSpinner } from '@/components/ui/FullPageSpinner';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { ChatMessage } from '@/components/assistant/ChatMessage';
import { ConversationHistory } from '@/components/assistant/ConversationHistory';
import { DocumentScopeSelector } from '@/components/assistant/DocumentScopeSelector';
import { SuggestedQuestions } from '@/components/assistant/SuggestedQuestions';
import { SourcePanel } from '@/components/assistant/SourcePanel';

export function AiAssistantPage() {
  const { data: session } = useSession();
  const workspaceId = session?.active_workspace_id ?? undefined;

  const conversationsQuery = useConversations(workspaceId);
  const documentsQuery = useDocuments(workspaceId, { page: 1 });
  const createConversation = useCreateConversation(workspaceId);

  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [pendingScope, setPendingScope] = useState<string[]>([]);
  const [draft, setDraft] = useState('');
  const [openCitation, setOpenCitation] = useState<AnswerCitation | null>(null);
  const [providerError, setProviderError] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const conversationQuery = useConversation(workspaceId, activeConversationId ?? undefined);
  const askQuestion = useAskQuestion(workspaceId);

  const documents = useMemo(() => documentsQuery.data?.results ?? [], [documentsQuery.data]);

  async function ensureConversation(): Promise<string> {
    if (activeConversationId) return activeConversationId;
    const created = await createConversation.mutateAsync({ document_scope: pendingScope });
    setActiveConversationId(created.id);
    return created.id;
  }

  async function handleAsk(question: string) {
    const trimmed = question.trim();
    if (!trimmed) return;
    setProviderError(false);
    setDraft('');

    const conversationId = await ensureConversation();
    const controller = new AbortController();
    abortRef.current = controller;

    askQuestion.mutate(
      { question: trimmed, conversationId, signal: controller.signal },
      {
        onError: (error) => {
          if (error instanceof DOMException && error.name === 'AbortError') return;
          if (error instanceof ApiError && error.code === 'provider_unavailable') {
            setProviderError(true);
          }
        },
      },
    );
  }

  function handleCancel() {
    abortRef.current?.abort();
  }

  function handleNewConversation() {
    setActiveConversationId(null);
    setPendingScope([]);
    setDraft('');
    setOpenCitation(null);
    setProviderError(false);
  }

  if (!workspaceId || conversationsQuery.isLoading) {
    return <FullPageSpinner />;
  }

  if (conversationsQuery.isError) {
    return <ErrorState title="Couldn't load your conversations" onRetry={() => void conversationsQuery.refetch()} />;
  }

  const messages = conversationQuery.data?.messages ?? [];
  const isAsking = askQuestion.isPending;

  return (
    <div className="grid h-full grid-cols-[220px_1fr] lg:grid-cols-[240px_1fr_320px]">
      <ConversationHistory
        conversations={conversationsQuery.data ?? []}
        activeId={activeConversationId}
        onSelect={setActiveConversationId}
        onNew={handleNewConversation}
      />

      <div className="flex min-h-0 flex-col">
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          {messages.length === 0 && (
            <EmptyState
              icon={Sparkles}
              title="Ask a grounded question"
              description="Answers cite the exact document and page they come from. Illustrative demo data — not a real generative model."
              action={<SuggestedQuestions onSelect={handleAsk} />}
            />
          )}
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message}
              activeCitationId={openCitation?.id ?? null}
              onOpenCitation={setOpenCitation}
            />
          ))}
          {isAsking && (
            <p role="status" className="text-sm text-text-secondary">
              Thinking…
            </p>
          )}
          {providerError && (
            <ErrorState
              title="The assistant is temporarily unavailable"
              description="Please try asking again."
              onRetry={() => void handleAsk(draft || messages[messages.length - 1]?.content || '')}
            />
          )}
        </div>

        <div className="border-t border-border bg-card p-3">
          {!activeConversationId && (
            <div className="mb-2">
              <DocumentScopeSelector
                documents={documents}
                selectedIds={pendingScope}
                onChange={setPendingScope}
              />
            </div>
          )}
          <form
            className="flex items-end gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              void handleAsk(draft);
            }}
          >
            <textarea
              aria-label="Ask a question"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  void handleAsk(draft);
                }
              }}
              rows={2}
              placeholder="Ask about your documents…"
              className="h-16 w-full resize-none rounded-md border border-border bg-card px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            />
            {isAsking ? (
              <Button type="button" variant="secondary" onClick={handleCancel}>
                <Square className="mr-1.5 size-4" /> Cancel
              </Button>
            ) : (
              <Button type="submit" disabled={!draft.trim()}>
                <Send className="mr-1.5 size-4" /> Ask
              </Button>
            )}
          </form>
        </div>
      </div>

      {openCitation && (
        <div className="hidden lg:block">
          <SourcePanel
            workspaceId={workspaceId}
            documentId={openCitation.document_id}
            page={openCitation.page_number}
            onClose={() => setOpenCitation(null)}
          />
        </div>
      )}
    </div>
  );
}
