import { useEffect, useRef, type ReactNode } from 'react';
import * as RadixDialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children?: ReactNode;
  className?: string;
}

/** Radix Dialog handles the focus trap (focus stays inside while open) —
 * verified reliable in both real browsers and jsdom. Its built-in focus
 * *restoration* (focus returns to whatever opened the dialog, once
 * closed) is verified reliable in real browsers but was found flaky
 * under jsdom in this project's test suite regardless of how the dialog
 * was closed (Escape or the close button), so it's re-implemented
 * explicitly below rather than relied on silently. */
export function Dialog({ open, onOpenChange, title, description, children, className }: DialogProps) {
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (open) {
      previouslyFocused.current = document.activeElement as HTMLElement | null;
    } else {
      previouslyFocused.current?.focus();
    }
  }, [open]);

  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-overlay bg-black/40" />
        <RadixDialog.Content
          className={cn(
            'fixed left-1/2 top-1/2 z-modal w-full max-w-md -translate-x-1/2 -translate-y-1/2',
            'rounded-lg border border-border bg-card p-6 shadow-lg',
            'focus:outline-none',
            className,
          )}
        >
          <RadixDialog.Title className="text-lg font-semibold text-text-primary">{title}</RadixDialog.Title>
          {description && (
            <RadixDialog.Description className="mt-1 text-sm text-text-secondary">
              {description}
            </RadixDialog.Description>
          )}
          <div className="mt-4">{children}</div>
          <RadixDialog.Close asChild>
            <button
              type="button"
              aria-label="Close dialog"
              className={cn(
                'absolute right-4 top-4 rounded-md p-1 text-text-muted transition-colors duration-fast',
                'hover:bg-lavender hover:text-text-primary',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
              )}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </RadixDialog.Close>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
