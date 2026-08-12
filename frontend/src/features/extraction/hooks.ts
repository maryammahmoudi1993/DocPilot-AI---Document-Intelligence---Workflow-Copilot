import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as extractionApi from './api';
import type { FieldCorrectionRequest, StatusTransitionRequest } from './types';

export const extractionQueryKey = (workspaceId: string | undefined, documentId: string | undefined) =>
  ['extraction', workspaceId, documentId] as const;

export function useExtractionQueue(workspaceId: string | undefined) {
  return useQuery({
    queryKey: ['extraction-queue', workspaceId],
    queryFn: () => extractionApi.getExtractionQueue(workspaceId!),
    enabled: Boolean(workspaceId),
  });
}

export function useExtraction(workspaceId: string | undefined, documentId: string | undefined) {
  return useQuery({
    queryKey: extractionQueryKey(workspaceId, documentId),
    queryFn: () => extractionApi.getExtraction(workspaceId!, documentId!),
    enabled: Boolean(workspaceId && documentId),
    retry: false,
  });
}

export function useCorrectField(workspaceId: string | undefined, documentId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fieldId, ...body }: FieldCorrectionRequest & { fieldId: string }) =>
      extractionApi.correctField(workspaceId!, documentId!, fieldId, body),
    onSuccess: () => {
      // The response is one field, but a correction also bumps the
      // extraction's version and re-runs validation — simplest correct
      // thing is to refetch the whole extraction rather than patch two
      // caches in sync.
      void queryClient.invalidateQueries({ queryKey: extractionQueryKey(workspaceId, documentId) });
    },
  });
}

export function useTransitionExtraction(workspaceId: string | undefined, documentId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: StatusTransitionRequest) => extractionApi.transitionExtraction(workspaceId!, documentId!, body),
    onSuccess: (extraction) => {
      queryClient.setQueryData(extractionQueryKey(workspaceId, documentId), extraction);
      void queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] });
    },
  });
}
