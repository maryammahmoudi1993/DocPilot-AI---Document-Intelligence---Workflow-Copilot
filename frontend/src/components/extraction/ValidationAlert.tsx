import { AlertTriangle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ValidationIssue } from '@/features/extraction/types';

export interface ValidationAlertProps {
  issues: ValidationIssue[];
  className?: string;
}

/** Renders every open validation issue for the extraction — errors
 * (block approval) styled distinctly from warnings (informational
 * only). See backend apps/extraction/services.run_validations for the
 * rules these come from. */
export function ValidationAlert({ issues, className }: ValidationAlertProps) {
  if (issues.length === 0) return null;

  return (
    <div role="alert" className={cn('space-y-2', className)}>
      {issues.map((issue) => {
        const isError = issue.severity === 'error';
        return (
          <div
            key={issue.id}
            className={cn(
              'flex items-start gap-2 rounded-lg border px-3 py-2 text-sm',
              isError
                ? 'border-status-failed-bg bg-status-failed-bg text-status-failed'
                : 'border-status-review-bg bg-status-review-bg text-status-review',
            )}
          >
            {isError ? (
              <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            ) : (
              <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            )}
            <span>{issue.message}</span>
          </div>
        );
      })}
    </div>
  );
}
