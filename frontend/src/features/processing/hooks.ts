import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as processingApi from './api';
import { TERMINAL_STAGES, type ProcessingJob } from './types';

export const processingStatusQueryKey = (workspaceId: string | undefined, documentId: string | undefined) =>
  ['processing-status', workspaceId, documentId] as const;

const MAX_POLL_INTERVAL_MS = 8000;
const MIN_POLL_INTERVAL_MS = 1000;

/**
 * Polls `/processing/` while the job is still running, with capped
 * exponential backoff (1s, 2s, 4s, 8s, 8s, ...) rather than a fixed
 * interval — a document that takes a while to process shouldn't hammer
 * the API once a second the whole time. Polling stops entirely (no
 * further requests at all) once the job reaches a terminal stage, and
 * — because this is plain TanStack Query `refetchInterval`, not a
 * hand-rolled `setInterval` — it also stops automatically the moment
 * the component using this hook unmounts or navigates away; no manual
 * cleanup needed.
 */
export function useProcessingStatus(workspaceId: string | undefined, documentId: string | undefined) {
  return useQuery({
    queryKey: processingStatusQueryKey(workspaceId, documentId),
    queryFn: () => processingApi.getProcessingStatus(workspaceId!, documentId!),
    enabled: Boolean(workspaceId && documentId),
    retry: false,
    refetchInterval: (query) => {
      const stage = query.state.data?.stage;
      if (!stage || TERMINAL_STAGES.includes(stage)) return false;
      const attempt = Math.max(0, query.state.dataUpdateCount - 1);
      return Math.min(MIN_POLL_INTERVAL_MS * 2 ** attempt, MAX_POLL_INTERVAL_MS);
    },
    refetchIntervalInBackground: false,
  });
}

export function useRetryProcessing(workspaceId: string | undefined, documentId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => processingApi.retryProcessing(workspaceId!, documentId!),
    onSuccess: (job: ProcessingJob) => {
      queryClient.setQueryData(processingStatusQueryKey(workspaceId, documentId), job);
      void queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] });
    },
  });
}
