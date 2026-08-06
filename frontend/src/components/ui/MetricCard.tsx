import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface MetricCardProps {
  label: string;
  value: string;
  icon?: LucideIcon;
  trend?: { direction: 'up' | 'down'; label: string };
  /** Illustrative-metric labeling — see project rules on not presenting
   * sample data as verified fact. Defaults on because most metrics in
   * this portfolio app are sample data until a phase wires real numbers. */
  isSample?: boolean;
  className?: string;
}

export function MetricCard({ label, value, icon: Icon, trend, isSample = true, className }: MetricCardProps) {
  return (
    <div className={cn('rounded-lg border border-border bg-card p-5 shadow-sm', className)}>
      <div className="flex items-center justify-between">
        <span className="text-sm text-text-secondary">{label}</span>
        {Icon && (
          <div className="rounded-md bg-primary-soft p-1.5">
            <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
          </div>
        )}
      </div>
      <div className="mt-2 text-2xl font-semibold text-text-primary">{value}</div>
      <div className="mt-1 flex items-center gap-2">
        {trend && (
          <span
            className={cn(
              'text-xs font-medium',
              trend.direction === 'up' ? 'text-status-approved' : 'text-status-failed',
            )}
          >
            {trend.direction === 'up' ? '▲' : '▼'} {trend.label}
          </span>
        )}
        {isSample && <span className="text-xs text-text-muted">Illustrative metric</span>}
      </div>
    </div>
  );
}
