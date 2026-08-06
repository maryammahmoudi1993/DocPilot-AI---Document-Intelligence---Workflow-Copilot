import { forwardRef, type InputHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Renders a visually-styled error state and sets aria-invalid — pair
   * with a real error message (see ErrorState / form field description)
   * referenced via aria-describedby at the call site. */
  hasError?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, hasError = false, ...props }, ref) => {
    return (
      <input
        ref={ref}
        aria-invalid={hasError || undefined}
        className={cn(
          'h-10 w-full rounded-md border bg-card px-3 text-sm text-text-primary placeholder:text-text-muted',
          'transition-colors duration-fast',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
          'disabled:cursor-not-allowed disabled:opacity-50',
          hasError ? 'border-status-failed' : 'border-border',
          className,
        )}
        {...props}
      />
    );
  },
);
Input.displayName = 'Input';
