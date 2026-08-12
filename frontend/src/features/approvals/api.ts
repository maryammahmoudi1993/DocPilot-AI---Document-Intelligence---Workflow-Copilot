import { apiRequest } from '@/lib/apiClient';
import type {
  ApprovalComment,
  ApprovalDecisionRequest,
  ApprovalRequest,
  ApprovalStatus,
} from './types';

export function listApprovals(
  workspaceId: string,
  status?: ApprovalStatus,
): Promise<ApprovalRequest[]> {
  const query = status ? `?status=${status}` : '';
  return apiRequest<ApprovalRequest[]>(`/workspaces/${workspaceId}/approvals/${query}`);
}

export function getApproval(workspaceId: string, approvalId: string): Promise<ApprovalRequest> {
  return apiRequest<ApprovalRequest>(`/workspaces/${workspaceId}/approvals/${approvalId}/`);
}

export function decideApproval(
  workspaceId: string,
  approvalId: string,
  body: ApprovalDecisionRequest,
): Promise<ApprovalRequest> {
  return apiRequest<ApprovalRequest>(`/workspaces/${workspaceId}/approvals/${approvalId}/decide/`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function addApprovalComment(
  workspaceId: string,
  approvalId: string,
  body: string,
): Promise<ApprovalComment> {
  return apiRequest<ApprovalComment>(
    `/workspaces/${workspaceId}/approvals/${approvalId}/comments/`,
    {
      method: 'POST',
      body: JSON.stringify({ body }),
    },
  );
}
