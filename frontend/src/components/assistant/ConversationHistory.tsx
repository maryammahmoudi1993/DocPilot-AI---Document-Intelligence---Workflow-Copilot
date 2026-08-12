import { MessageSquarePlus } from 'lucide-react';
import type { Conversation } from '@/features/assistant/types';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

export interface ConversationHistoryProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export function ConversationHistory({ conversations, activeId, onSelect, onNew }: ConversationHistoryProps) {
  return (
    <div className="flex h-full flex-col border-r border-border bg-sidebar">
      <div className="p-3">
        <Button type="button" variant="secondary" size="sm" className="w-full" onClick={onNew}>
          <MessageSquarePlus className="mr-1.5 size-4" /> New conversation
        </Button>
      </div>
      <nav aria-label="Conversation history" className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        {conversations.length === 0 && (
          <p className="px-2 py-1 text-xs text-text-muted">No conversations yet.</p>
        )}
        <ul className="space-y-1">
          {conversations.map((conversation) => (
            <li key={conversation.id}>
              <button
                type="button"
                onClick={() => onSelect(conversation.id)}
                className={cn(
                  'w-full rounded-md px-2.5 py-2 text-left text-sm transition-colors duration-fast',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                  activeId === conversation.id
                    ? 'bg-primary-soft text-primary'
                    : 'text-text-secondary hover:bg-lavender hover:text-text-primary',
                )}
              >
                {conversation.title || 'Untitled conversation'}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
