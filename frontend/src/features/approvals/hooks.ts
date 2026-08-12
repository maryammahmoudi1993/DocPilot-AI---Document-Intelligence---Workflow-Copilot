import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as approvalsApi from './api';
import type { ApprovalDecisionRequest, ApprovalStatus } from './types';

export const approvalsQueryKey = (workspaceId: string | undefined, status?: ApprovalStatus) =>
  ['approvals', workspaceId, status] as const;

export const approvalQueryKey = (workspaceId: string | undefined, approvalId: string | undefined) =>
  ['approval', workspaceId, approvalId] as const;

export function useApprovals(workspaceId: string | undefined, status?: ApprovalStatus) {
  return useQuery({
    queryKey: approvalsQueryKey(workspaceId, status),
    queryFn: () => approvalsApi.listApprovals(workspaceId!, status),
    enabled: Boolean(workspaceId),
  });
}

export function useApproval(workspaceId: string | undefined, approvalId: string | undefined) {
  return useQuery({
    queryKey: approvalQueryKey(workspaceId, approvalId),
    queryFn: () => approvalsApi.getApproval(workspaceId!, approvalId!),
    enabled: Boolean(workspaceId && approvalId),
  });
}

export function useDecideApproval(workspaceId: string | undefined, approvalId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ApprovalDecisionRequest) =>
      approvalsApi.decideApproval(workspaceId!, approvalId!, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: approvalQueryKey(workspaceId, approvalId) });
      void queryClient.invalidateQueries({ queryKey: ['approvals', workspaceId] });
    },
  });
}

export function useAddApprovalComment(
  workspaceId: string | undefined,
  approvalId: string | undefined,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => approvalsApi.addApprovalComment(workspaceId!, approvalId!, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: approvalQueryKey(workspaceId, approvalId) });
    },
  });
}
