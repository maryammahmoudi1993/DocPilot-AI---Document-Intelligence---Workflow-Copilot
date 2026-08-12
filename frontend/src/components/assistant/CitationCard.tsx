import { FileText } from 'lucide-react';
import type { AnswerCitation } from '@/features/assistant/types';
import { cn } from '@/lib/utils';

export interface CitationCardProps {
  citation: AnswerCitation;
  isActive: boolean;
  onOpen: (citation: AnswerCitation) => void;
}

/** One citation chip under an assistant answer. Keyboard-accessible (a
 * real `<button>`, reachable by Tab, activated by Enter/Space) — opens
 * the SourcePanel at the cited document and page. */
export function CitationCard({ citation, isActive, onOpen }: CitationCardProps) {
  return (
    <button
      type="button"
      onClick={() => onOpen(citation)}
      aria-pressed={isActive}
      className={cn(
        'flex w-full items-start gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors duration-fast',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
        isActive ? 'border-primary bg-primary-soft/40' : 'border-border bg-card hover:bg-lavender',
      )}
    >
      <FileText className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
      <span>
        <span className="font-medium text-text-primary">
          {citation.filename} · p.{citation.page_number}
        </span>
        <span className="mt-0.5 block text-text-secondary">{citation.snippet}</span>
      </span>
    </button>
  );
}
