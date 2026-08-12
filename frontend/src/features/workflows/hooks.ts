import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as workflowsApi from './api';
import type { SaveDraftRequest } from './types';

export const workflowsQueryKey = (workspaceId: string | undefined) =>
  ['workflows', workspaceId] as const;

export const workflowQueryKey = (workspaceId: string | undefined, workflowId: string | undefined) =>
  ['workflow', workspaceId, workflowId] as const;

export const workflowRunsQueryKey = (workspaceId: string | undefined, workflowId: string | undefined) =>
  ['workflow-runs', workspaceId, workflowId] as const;

export function useWorkflows(workspaceId: string | undefined) {
  return useQuery({
    queryKey: workflowsQueryKey(workspaceId),
    queryFn: () => workflowsApi.listWorkflows(workspaceId!),
    enabled: Boolean(workspaceId),
  });
}

export function useWorkflow(workspaceId: string | undefined, workflowId: string | undefined) {
  return useQuery({
    queryKey: workflowQueryKey(workspaceId, workflowId),
    queryFn: () => workflowsApi.getWorkflow(workspaceId!, workflowId!),
    enabled: Boolean(workspaceId && workflowId),
  });
}

export function useCreateWorkflow(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => workflowsApi.createWorkflow(workspaceId!, name),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workflowsQueryKey(workspaceId) });
    },
  });
}

export function useSaveDraft(workspaceId: string | undefined, workflowId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: SaveDraftRequest) => workflowsApi.saveDraft(workspaceId!, workflowId!, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workflowQueryKey(workspaceId, workflowId) });
    },
  });
}

export function useActivateWorkflow(workspaceId: string | undefined, workflowId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => workflowsApi.activateWorkflow(workspaceId!, workflowId!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workflowQueryKey(workspaceId, workflowId) });
      void queryClient.invalidateQueries({ queryKey: workflowsQueryKey(workspaceId) });
    },
  });
}

export function useDeactivateWorkflow(workspaceId: string | undefined, workflowId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => workflowsApi.deactivateWorkflow(workspaceId!, workflowId!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workflowQueryKey(workspaceId, workflowId) });
      void queryClient.invalidateQueries({ queryKey: workflowsQueryKey(workspaceId) });
    },
  });
}

export function useTestRunWorkflow(workspaceId: string | undefined, workflowId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (triggerContext: Record<string, unknown>) =>
      workflowsApi.testRunWorkflow(workspaceId!, workflowId!, triggerContext),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workflowRunsQueryKey(workspaceId, workflowId) });
    },
  });
}

export function useWorkflowRuns(workspaceId: string | undefined, workflowId: string | undefined) {
  return useQuery({
    queryKey: workflowRunsQueryKey(workspaceId, workflowId),
    queryFn: () => workflowsApi.listWorkflowRuns(workspaceId!, workflowId!),
    enabled: Boolean(workspaceId && workflowId),
  });
}
