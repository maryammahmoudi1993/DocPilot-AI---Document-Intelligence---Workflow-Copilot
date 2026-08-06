import { useEffect, useRef, type ReactNode } from 'react';
import * as RadixDialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface DrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  side?: 'left' | 'right';
  children?: ReactNode;
  className?: string;
}

/** Slide-in panel built on Radix Dialog (same focus-trap guarantee as
 * Dialog; see Dialog.tsx for why focus restoration is re-implemented
 * explicitly instead of relied on from Radix alone). */
export function Drawer({ open, onOpenChange, title, side = 'left', children, className }: DrawerProps) {
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
            'fixed top-0 z-modal h-full w-72 bg-sidebar p-4 shadow-lg focus:outline-none',
            side === 'left' ? 'left-0' : 'right-0',
            className,
          )}
        >
          <div className="flex items-center justify-between">
            <RadixDialog.Title className="text-base font-semibold text-text-primary">{title}</RadixDialog.Title>
            <RadixDialog.Close asChild>
              <button
                type="button"
                aria-label="Close menu"
                className="rounded-md p-1 text-text-muted hover:bg-lavender hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </RadixDialog.Close>
          </div>
          <div className="mt-4">{children}</div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
