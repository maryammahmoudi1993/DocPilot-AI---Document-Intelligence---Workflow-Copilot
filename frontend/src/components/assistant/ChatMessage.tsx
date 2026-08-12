import { AlertCircle, Sparkles, User } from 'lucide-react';
import type { AnswerCitation, Message } from '@/features/assistant/types';
import { CitationCard } from './CitationCard';
import { cn } from '@/lib/utils';

export interface ChatMessageProps {
  message: Message;
  activeCitationId: string | null;
  onOpenCitation: (citation: AnswerCitation) => void;
}

export function ChatMessage({ message, activeCitationId, onOpenCitation }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      <div
        className={cn(
          'flex size-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary text-white' : 'bg-primary-soft text-primary',
        )}
        aria-hidden="true"
      >
        {isUser ? <User className="size-4" /> : <Sparkles className="size-4" />}
      </div>

      <div className={cn('max-w-2xl space-y-2', isUser && 'items-end text-right')}>
        <div
          className={cn(
            'whitespace-pre-wrap rounded-lg px-4 py-2.5 text-sm',
            isUser ? 'bg-primary text-white' : 'bg-card text-text-primary',
            message.is_insufficient_evidence && 'border border-status-review-bg bg-status-review-bg text-status-review',
          )}
        >
          {message.is_insufficient_evidence && !isUser && (
            <div className="mb-1 flex items-center gap-1 text-xs font-medium">
              <AlertCircle className="size-3.5" /> Insufficient evidence
            </div>
          )}
          {message.content}
        </div>

        {message.citations.length > 0 && (
          <div className="space-y-1.5">
            {message.citations.map((citation) => (
              <CitationCard
                key={citation.id}
                citation={citation}
                isActive={activeCitationId === citation.id}
                onOpen={onOpenCitation}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
