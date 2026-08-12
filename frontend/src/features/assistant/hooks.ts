import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as assistantApi from './api';
import type { AskQuestionRequest, ConversationCreateRequest } from './types';

export const conversationsQueryKey = (workspaceId: string | undefined) =>
  ['assistant-conversations', workspaceId] as const;

export const conversationQueryKey = (workspaceId: string | undefined, conversationId: string | undefined) =>
  ['assistant-conversation', workspaceId, conversationId] as const;

export function useConversations(workspaceId: string | undefined) {
  return useQuery({
    queryKey: conversationsQueryKey(workspaceId),
    queryFn: () => assistantApi.listConversations(workspaceId!),
    enabled: Boolean(workspaceId),
  });
}

export function useConversation(workspaceId: string | undefined, conversationId: string | undefined) {
  return useQuery({
    queryKey: conversationQueryKey(workspaceId, conversationId),
    queryFn: () => assistantApi.getConversation(workspaceId!, conversationId!),
    enabled: Boolean(workspaceId && conversationId),
  });
}

export function useCreateConversation(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ConversationCreateRequest) => assistantApi.createConversation(workspaceId!, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: conversationsQueryKey(workspaceId) });
    },
  });
}

/** Takes `conversationId` per-call (mutate-time), not hook-time — a
 * brand new conversation's id is only known at the moment the first
 * question in it is asked (see AiAssistantPage.handleAsk), after which
 * a hook bound to the *previous* render's conversationId would still be
 * stale even though a re-render with the new id hasn't landed yet. */
export function useAskQuestion(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      conversationId,
      signal,
      ...body
    }: AskQuestionRequest & { conversationId: string; signal?: AbortSignal }) =>
      assistantApi.askQuestion(workspaceId!, conversationId, body, signal),
    onSuccess: (_message, variables) => {
      void queryClient.invalidateQueries({
        queryKey: conversationQueryKey(workspaceId, variables.conversationId),
      });
      void queryClient.invalidateQueries({ queryKey: conversationsQueryKey(workspaceId) });
    },
  });
}
