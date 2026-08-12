import { AlertCircle } from 'lucide-react';

export interface ValidationMessagesProps {
  errors: string[];
}

export function ValidationMessages({ errors }: ValidationMessagesProps) {
  if (errors.length === 0) return null;

  return (
    <div role="alert" className="space-y-1 border-b border-status-failed-bg bg-status-failed-bg px-4 py-2">
      {errors.map((error) => (
        <div key={error} className="flex items-start gap-1.5 text-xs text-status-failed">
          <AlertCircle className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          {error}
        </div>
      ))}
    </div>
  );
}
