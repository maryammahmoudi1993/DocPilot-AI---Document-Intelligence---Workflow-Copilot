import type { LucideIcon } from 'lucide-react';
import { PageHeader } from './PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';

export interface RoutePlaceholderProps {
  title: string;
  description: string;
  icon: LucideIcon;
}

/** Every product route uses this until its owning phase replaces the body
 * with real content — the shell (PageHeader + AppShell) is already final,
 * only what's below the header is a placeholder. */
export function RoutePlaceholder({ title, description, icon }: RoutePlaceholderProps) {
  return (
    <div className="space-y-6">
      <PageHeader title={title} description={description} />
      <EmptyState
        icon={icon}
        title="Coming in a later phase"
        description="This screen's shell is ready; its real functionality is implemented in a later phase of this project."
      />
    </div>
  );
}
