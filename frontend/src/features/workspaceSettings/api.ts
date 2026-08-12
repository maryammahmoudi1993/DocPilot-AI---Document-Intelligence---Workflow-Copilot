import { apiRequest } from '@/lib/apiClient';
import type { WorkspaceSettings, WorkspaceSettingsUpdate } from './types';

export function getWorkspaceSettings(workspaceId: string): Promise<WorkspaceSettings> {
  return apiRequest<WorkspaceSettings>(`/workspaces/${workspaceId}/settings/`);
}

export function updateWorkspaceSettings(
  workspaceId: string,
  body: WorkspaceSettingsUpdate,
): Promise<WorkspaceSettings> {
  return apiRequest<WorkspaceSettings>(`/workspaces/${workspaceId}/settings/`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}
