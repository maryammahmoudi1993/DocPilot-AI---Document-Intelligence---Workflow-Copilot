import { CheckCircle2, Clock, XCircle } from 'lucide-react';
import type { WorkflowRun } from '@/features/workflows/types';
import { cn } from '@/lib/utils';

export interface ExecutionLogProps {
  runs: WorkflowRun[];
}

const STATUS_ICON = {
  completed: CheckCircle2,
  failed: XCircle,
  queued: Clock,
  running: Clock,
};

const STATUS_CLASSES = {
  completed: 'text-status-approved',
  failed: 'text-status-failed',
  queued: 'text-text-muted',
  running: 'text-status-processing',
};

export function ExecutionLog({ runs }: ExecutionLogProps) {
  if (runs.length === 0) {
    return <p className="p-4 text-sm text-text-muted">No runs yet — test or trigger this workflow to see one here.</p>;
  }

  return (
    <ul className="divide-y divide-divider">
      {runs.map((run) => {
        const Icon = STATUS_ICON[run.status];
        return (
          <li key={run.id} className="p-3">
            <div className="flex items-center gap-2 text-sm">
              <Icon className={cn('size-4', STATUS_CLASSES[run.status])} aria-hidden="true" />
              <span className="font-medium text-text-primary">
                {run.is_test_run ? 'Test run' : 'Run'} — {run.status}
              </span>
              <span className="text-xs text-text-muted">{new Date(run.created_at).toLocaleString()}</span>
            </div>
            {run.step_runs.length > 0 && (
              <ol className="mt-1.5 ml-6 space-y-0.5 text-xs text-text-secondary">
                {run.step_runs.map((step) => (
                  <li key={step.id}>
                    {step.node_key} ({step.node_kind}) — {step.status}
                    {step.error_code && ` (${step.error_code})`}
                  </li>
                ))}
              </ol>
            )}
          </li>
        );
      })}
    </ul>
  );
}
