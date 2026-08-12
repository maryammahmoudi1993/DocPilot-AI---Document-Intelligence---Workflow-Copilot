import { apiRequest } from '@/lib/apiClient';
import type {
  AskQuestionRequest,
  Conversation,
  ConversationCreateRequest,
  ConversationDetail,
  Message,
} from './types';

export function listConversations(workspaceId: string): Promise<Conversation[]> {
  return apiRequest<Conversation[]>(`/workspaces/${workspaceId}/assistant/conversations/`);
}

export function createConversation(
  workspaceId: string,
  body: ConversationCreateRequest,
): Promise<ConversationDetail> {
  return apiRequest<ConversationDetail>(`/workspaces/${workspaceId}/assistant/conversations/`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function getConversation(workspaceId: string, conversationId: string): Promise<ConversationDetail> {
  return apiRequest<ConversationDetail>(
    `/workspaces/${workspaceId}/assistant/conversations/${conversationId}/`,
  );
}

export function askQuestion(
  workspaceId: string,
  conversationId: string,
  body: AskQuestionRequest,
  signal?: AbortSignal,
): Promise<Message> {
  return apiRequest<Message>(
    `/workspaces/${workspaceId}/assistant/conversations/${conversationId}/messages/`,
    { method: 'POST', body: JSON.stringify(body), signal },
  );
}
