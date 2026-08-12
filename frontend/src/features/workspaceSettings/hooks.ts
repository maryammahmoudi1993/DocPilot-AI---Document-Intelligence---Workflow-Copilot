import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as workspaceSettingsApi from './api';
import type { WorkspaceSettingsUpdate } from './types';

export const workspaceSettingsQueryKey = (workspaceId: string | undefined) =>
  ['workspace-settings', workspaceId] as const;

export function useWorkspaceSettings(workspaceId: string | undefined) {
  return useQuery({
    queryKey: workspaceSettingsQueryKey(workspaceId),
    queryFn: () => workspaceSettingsApi.getWorkspaceSettings(workspaceId!),
    enabled: Boolean(workspaceId),
  });
}

export function useUpdateWorkspaceSettings(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkspaceSettingsUpdate) =>
      workspaceSettingsApi.updateWorkspaceSettings(workspaceId!, body),
    onSuccess: (updated) => {
      queryClient.setQueryData(workspaceSettingsQueryKey(workspaceId), updated);
    },
  });
}
