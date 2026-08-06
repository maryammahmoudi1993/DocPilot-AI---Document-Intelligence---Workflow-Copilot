import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

/** `motion-reduce:animate-none` respects prefers-reduced-motion (see also
 * the global rule in src/index.css) instead of relying on callers to
 * remember it per usage. */
export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="presentation"
      aria-hidden="true"
      className={cn('animate-pulse rounded-md bg-lavender motion-reduce:animate-none', className)}
      {...props}
    />
  );
}
