import { useQuery } from '@tanstack/react-query';
import * as analyticsApi from './api';
import type { AnalyticsDateRange } from './types';

export const dashboardSummaryQueryKey = (workspaceId: string | undefined) =>
  ['dashboard-summary', workspaceId] as const;

export const analyticsOverviewQueryKey = (
  workspaceId: string | undefined,
  range: AnalyticsDateRange,
) => ['analytics-overview', workspaceId, range] as const;

export function useDashboardSummary(workspaceId: string | undefined) {
  return useQuery({
    queryKey: dashboardSummaryQueryKey(workspaceId),
    queryFn: () => analyticsApi.getDashboardSummary(workspaceId!),
    enabled: Boolean(workspaceId),
  });
}

export function useAnalyticsOverview(
  workspaceId: string | undefined,
  range: AnalyticsDateRange = {},
) {
  return useQuery({
    queryKey: analyticsOverviewQueryKey(workspaceId, range),
    queryFn: () => analyticsApi.getAnalyticsOverview(workspaceId!, range),
    enabled: Boolean(workspaceId),
  });
}
