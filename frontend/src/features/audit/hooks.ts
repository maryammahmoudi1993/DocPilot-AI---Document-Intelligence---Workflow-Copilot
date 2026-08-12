import { useQuery } from '@tanstack/react-query';
import * as auditApi from './api';
import type { AuditEventFilters } from './types';

export const auditEventsQueryKey = (workspaceId: string | undefined, filters: AuditEventFilters) =>
  ['audit-events', workspaceId, filters] as const;

export function useAuditEvents(workspaceId: string | undefined, filters: AuditEventFilters = {}) {
  return useQuery({
    queryKey: auditEventsQueryKey(workspaceId, filters),
    queryFn: () => auditApi.listAuditEvents(workspaceId!, filters),
    enabled: Boolean(workspaceId),
  });
}
