import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface FilterBarProps {
  children: ReactNode;
  className?: string;
}

/** Layout shell only — individual filters (Select, SearchInput, date
 * range, etc.) are composed by the page that needs them. Keeping filter
 * *state* (e.g. syncing to URL query params) out of this component since
 * that's page-specific business logic, not shared UI. */
export function FilterBar({ children, className }: FilterBarProps) {
  return (
    <div
      role="search"
      className={cn(
        'flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card p-3',
        className,
      )}
    >
      {children}
    </div>
  );
}
