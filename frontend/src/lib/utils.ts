import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind class lists, resolving conflicting utilities (e.g.
 * `cn('p-2', condition && 'p-4')` keeps only 'p-4' when condition is true)
 * instead of leaving both in the class string.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
