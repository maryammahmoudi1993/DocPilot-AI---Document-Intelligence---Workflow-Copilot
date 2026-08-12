import { useState } from 'react';
import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useSession } from '@/features/auth/hooks';
import { useAnalyticsOverview } from '@/features/analytics/hooks';
import { PageHeader } from '@/components/layout/PageHeader';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { BarChart3 } from 'lucide-react';

const PIE_COLORS = ['#7257F5', '#65A7F7', '#65C99B', '#F2C95F', '#F17691', '#A3A1AF'];

function formatPercent(value: number | null): string {
  return value === null ? '—' : `${Math.round(value * 100)}%`;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return '—';
  const hours = seconds / 3600;
  if (hours < 1) return `${Math.round(seconds / 60)} min`;
  if (hours < 48) return `${hours.toFixed(1)} hr`;
  return `${Math.round(hours / 24)} days`;
}

export function AnalyticsPage() {
  const { data: session } = useSession();
  const workspaceId = session?.active_workspace_id ?? undefined;

  const [since, setSince] = useState('');
  const [until, setUntil] = useState('');
  const overviewQuery = useAnalyticsOverview(workspaceId, {
    since: since || undefined,
    until: until || undefined,
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Analytics"
        description="Illustrative operational metrics for this demo workspace, computed from real activity."
      />

      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="analytics-since" className="mb-1 block text-xs font-medium text-text-secondary">
            Since
          </label>
          <Input id="analytics-since" type="date" value={since} onChange={(e) => setSince(e.target.value)} />
        </div>
        <div>
          <label htmlFor="analytics-until" className="mb-1 block text-xs font-medium text-text-secondary">
            Until
          </label>
          <Input id="analytics-until" type="date" value={until} onChange={(e) => setUntil(e.target.value)} />
        </div>
      </div>

      {overviewQuery.isPending && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Skeleton className="h-64 w-full rounded-lg" />
          <Skeleton className="h-64 w-full rounded-lg" />
        </div>
      )}

      {overviewQuery.isError && (
        <ErrorState description="Could not load analytics." onRetry={() => overviewQuery.refetch()} />
      )}

      {overviewQuery.data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Extraction confidence"
              value={formatPercent(overviewQuery.data.extraction_accuracy.average_confidence)}
              note="Illustrative metric"
            />
            <StatCard
              label="Review rate"
              value={formatPercent(overviewQuery.data.review_rate.review_rate)}
            />
            <StatCard
              label="Workflow success rate"
              value={formatPercent(overviewQuery.data.workflow_success.success_rate)}
            />
            <StatCard
              label="Avg. approval time"
              value={formatDuration(overviewQuery.data.approval_duration.average_duration_seconds)}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.6fr_1fr]">
            <div className="rounded-lg border border-border bg-card p-5">
              <h2 className="mb-4 text-sm font-semibold text-text-primary">Processing trend</h2>
              {overviewQuery.data.processing_trends.every((point) => point.total === 0) ? (
                <EmptyState icon={BarChart3} title="No processing activity in this range" />
              ) : (
                <div className="h-56 w-full motion-reduce:[&_*]:!transition-none motion-reduce:[&_*]:!animate-none">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={overviewQuery.data.processing_trends}>
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 11, fill: '#A3A1AF' }}
                        tickFormatter={(value: string) =>
                          new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                        }
                      />
                      <YAxis tick={{ fontSize: 11, fill: '#A3A1AF' }} allowDecimals={false} />
                      <Tooltip
                        labelFormatter={(value) =>
                          typeof value === 'string' ? new Date(value).toLocaleDateString() : value
                        }
                      />
                      <Area
                        type="monotone"
                        dataKey="total"
                        stroke="#7257F5"
                        fill="#7257F5"
                        fillOpacity={0.08}
                        strokeWidth={2}
                        isAnimationActive={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            <div className="rounded-lg border border-border bg-card p-5">
              <h2 className="mb-4 text-sm font-semibold text-text-primary">Documents by type</h2>
              {overviewQuery.data.document_type_counts.length === 0 ? (
                <EmptyState icon={BarChart3} title="No classified documents yet" />
              ) : (
                <div className="flex items-center gap-4">
                  <div className="h-40 w-40 shrink-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={overviewQuery.data.document_type_counts}
                          dataKey="count"
                          nameKey="document_type"
                          innerRadius={40}
                          outerRadius={70}
                          isAnimationActive={false}
                        >
                          {overviewQuery.data.document_type_counts.map((entry, index) => (
                            <Cell
                              key={entry.document_type ?? 'unknown'}
                              fill={PIE_COLORS[index % PIE_COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <ul className="flex flex-col gap-2 text-xs">
                    {overviewQuery.data.document_type_counts.map((entry, index) => (
                      <li key={entry.document_type ?? 'unknown'} className="flex items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 shrink-0 rounded-sm"
                          style={{ backgroundColor: PIE_COLORS[index % PIE_COLORS.length] }}
                        />
                        <span className="capitalize text-text-primary">
                          {entry.document_type ?? 'unclassified'}
                        </span>
                        <span className="text-text-muted">· {entry.count}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <p className="text-sm text-text-secondary">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-text-primary">{value}</p>
      {note && <p className="mt-1 text-xs text-text-muted">{note}</p>}
    </div>
  );
}
