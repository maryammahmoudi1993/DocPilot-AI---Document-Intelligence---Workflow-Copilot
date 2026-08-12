import { apiRequest } from '@/lib/apiClient';
import type { AuditEventFilters, AuditEventPage } from './types';

export function listAuditEvents(
  workspaceId: string,
  filters: AuditEventFilters = {},
): Promise<AuditEventPage> {
  const params = new URLSearchParams();
  if (filters.event_type) params.set('event_type', filters.event_type);
  if (filters.since) params.set('since', filters.since);
  if (filters.until) params.set('until', filters.until);
  if (filters.page) params.set('page', String(filters.page));
  const query = params.toString();
  return apiRequest<AuditEventPage>(
    `/workspaces/${workspaceId}/audit-events/${query ? `?${query}` : ''}`,
  );
}
