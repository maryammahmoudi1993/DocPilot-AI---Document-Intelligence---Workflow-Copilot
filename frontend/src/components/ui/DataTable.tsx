import type { ReactNode, TableHTMLAttributes, ThHTMLAttributes, TdHTMLAttributes } from 'react';
import { ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Presentational table primitives only — no data-fetching or sort-state
 * logic lives here (that belongs to whichever page wires these up to
 * TanStack Table / TanStack Query once real data exists). This shell's
 * job is to guarantee every table in the product has an accessible
 * caption, real <th> scope, and a consistent sortable-header affordance.
 */

export interface DataTableProps extends TableHTMLAttributes<HTMLTableElement> {
  /** Visually hidden by default via `caption-hidden`, but always present
   * — screen readers need a table name even when the page title already
   * makes it visually obvious. */
  caption: string;
  captionVisible?: boolean;
  children: ReactNode;
}

export function DataTable({ caption, captionVisible = false, className, children, ...props }: DataTableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-card">
      <table className={cn('w-full text-left text-sm', className)} {...props}>
        <caption className={cn('p-3 text-left text-sm text-text-secondary', !captionVisible && 'sr-only')}>
          {caption}
        </caption>
        {children}
      </table>
    </div>
  );
}

export function DataTableHead({ children }: { children: ReactNode }) {
  return <thead className="border-b border-border bg-lavender/50">{children}</thead>;
}

export function DataTableBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-divider">{children}</tbody>;
}

export function DataTableRow({ children, className, ...props }: TableHTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr className={cn('hover:bg-lavender/40', className)} {...props}>
      {children}
    </tr>
  );
}

export function DataTableCell({ children, className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn('px-4 py-3 text-text-primary', className)} {...props}>
      {children}
    </td>
  );
}

export interface DataTableHeaderCellProps extends ThHTMLAttributes<HTMLTableCellElement> {
  children: ReactNode;
  sortDirection?: 'asc' | 'desc' | false;
  onSort?: () => void;
}

export function DataTableHeaderCell({
  children,
  className,
  sortDirection,
  onSort,
  ...props
}: DataTableHeaderCellProps) {
  const SortIcon = sortDirection === 'asc' ? ArrowUp : sortDirection === 'desc' ? ArrowDown : ArrowUpDown;

  return (
    <th
      scope="col"
      aria-sort={sortDirection ? (sortDirection === 'asc' ? 'ascending' : 'descending') : undefined}
      className={cn('px-4 py-3 font-medium text-text-secondary', className)}
      {...props}
    >
      {onSort ? (
        <button
          type="button"
          onClick={onSort}
          className="inline-flex items-center gap-1 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-sm"
        >
          {children}
          <SortIcon className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      ) : (
        children
      )}
    </th>
  );
}
