import { apiRequest } from '@/lib/apiClient';
import type { AnalyticsDateRange, AnalyticsOverview, DashboardSummary } from './types';

export function getDashboardSummary(workspaceId: string): Promise<DashboardSummary> {
  return apiRequest<DashboardSummary>(`/workspaces/${workspaceId}/dashboard/`);
}

export function getAnalyticsOverview(
  workspaceId: string,
  range: AnalyticsDateRange = {},
): Promise<AnalyticsOverview> {
  const params = new URLSearchParams();
  if (range.since) params.set('since', range.since);
  if (range.until) params.set('until', range.until);
  const query = params.toString();
  return apiRequest<AnalyticsOverview>(
    `/workspaces/${workspaceId}/analytics/${query ? `?${query}` : ''}`,
  );
}
