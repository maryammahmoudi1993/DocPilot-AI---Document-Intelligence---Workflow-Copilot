import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import type { AnswerCitation, Conversation, ConversationDetail, Message } from '@/features/assistant/types';
import { demoWorkspaces } from './handlers';

const API = config.apiBaseUrl;
const WORKSPACE_ID = demoWorkspaces[0]!.id;

function errorBody(code: string, message: string, details: unknown = null) {
  return { error: { code, message, details } };
}

export function buildCitation(overrides: Partial<AnswerCitation> = {}): AnswerCitation {
  return {
    id: 'citation-1',
    document_id: 'doc-1',
    filename: 'acme-invoice-0142.pdf',
    page_number: 1,
    snippet: 'Total due: $1,200.00',
    order: 0,
    ...overrides,
  };
}

export function buildAssistantMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: 'msg-assistant-1',
    role: 'assistant',
    content: 'Based on 1 matching passage — acme-invoice-0142.pdf (p.1) — the total due is $1,200.00.',
    is_insufficient_evidence: false,
    citations: [buildCitation()],
    created_at: '2026-08-12T00:00:01Z',
    ...overrides,
  };
}

export function buildConversation(overrides: Partial<ConversationDetail> = {}): ConversationDetail {
  return {
    id: 'conv-1',
    title: '',
    document_scope: [],
    messages: [],
    created_at: '2026-08-12T00:00:00Z',
    updated_at: '2026-08-12T00:00:00Z',
    ...overrides,
  };
}

export function conversationListHandler(conversations: Conversation[]) {
  return http.get(`${API}/workspaces/${WORKSPACE_ID}/assistant/conversations/`, () =>
    HttpResponse.json(conversations),
  );
}

export function createConversationHandler(conversation: ConversationDetail) {
  return http.post(`${API}/workspaces/${WORKSPACE_ID}/assistant/conversations/`, () =>
    HttpResponse.json(conversation, { status: 201 }),
  );
}

export function conversationDetailHandler(conversation: ConversationDetail) {
  return http.get(`${API}/workspaces/${WORKSPACE_ID}/assistant/conversations/:conversationId/`, () =>
    HttpResponse.json(conversation),
  );
}

export function askQuestionHandler(
  message: Message,
  options: { delayMs?: number; providerError?: boolean } = {},
) {
  return http.post(
    `${API}/workspaces/${WORKSPACE_ID}/assistant/conversations/:conversationId/messages/`,
    async () => {
      if (options.delayMs) {
        await new Promise((resolve) => setTimeout(resolve, options.delayMs));
      }
      if (options.providerError) {
        return HttpResponse.json(
          errorBody('provider_unavailable', 'The assistant is temporarily unavailable.'),
          { status: 503 },
        );
      }
      return HttpResponse.json(message, { status: 201 });
    },
  );
}
