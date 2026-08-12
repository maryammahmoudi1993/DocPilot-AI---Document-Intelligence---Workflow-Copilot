import { apiRequest } from '@/lib/apiClient';
import type {
  SaveDraftRequest,
  Workflow,
  WorkflowDetail,
  WorkflowRun,
  WorkflowVersionWithValidation,
} from './types';

export function listWorkflows(workspaceId: string): Promise<Workflow[]> {
  return apiRequest<Workflow[]>(`/workspaces/${workspaceId}/workflows/`);
}

export function createWorkflow(workspaceId: string, name: string): Promise<WorkflowDetail> {
  return apiRequest<WorkflowDetail>(`/workspaces/${workspaceId}/workflows/`, {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export function getWorkflow(workspaceId: string, workflowId: string): Promise<WorkflowDetail> {
  return apiRequest<WorkflowDetail>(`/workspaces/${workspaceId}/workflows/${workflowId}/`);
}

export function saveDraft(
  workspaceId: string,
  workflowId: string,
  body: SaveDraftRequest,
): Promise<WorkflowVersionWithValidation> {
  return apiRequest<WorkflowVersionWithValidation>(
    `/workspaces/${workspaceId}/workflows/${workflowId}/draft/`,
    { method: 'PUT', body: JSON.stringify(body) },
  );
}

export function activateWorkflow(workspaceId: string, workflowId: string) {
  return apiRequest(`/workspaces/${workspaceId}/workflows/${workflowId}/activate/`, {
    method: 'POST',
  });
}

export function deactivateWorkflow(workspaceId: string, workflowId: string): Promise<Workflow> {
  return apiRequest<Workflow>(`/workspaces/${workspaceId}/workflows/${workflowId}/deactivate/`, {
    method: 'POST',
  });
}

export function testRunWorkflow(
  workspaceId: string,
  workflowId: string,
  triggerContext: Record<string, unknown>,
): Promise<WorkflowRun> {
  return apiRequest<WorkflowRun>(`/workspaces/${workspaceId}/workflows/${workflowId}/test-run/`, {
    method: 'POST',
    body: JSON.stringify({ trigger_context: triggerContext }),
  });
}

export function listWorkflowRuns(workspaceId: string, workflowId: string): Promise<WorkflowRun[]> {
  return apiRequest<WorkflowRun[]>(`/workspaces/${workspaceId}/workflows/${workflowId}/runs/`);
}
