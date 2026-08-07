import { Loader2 } from 'lucide-react';

export function FullPageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-page" role="status" aria-live="polite">
      <Loader2 className="h-6 w-6 animate-spin text-primary" aria-hidden="true" />
      <span className="sr-only">Loading…</span>
    </div>
  );
}
