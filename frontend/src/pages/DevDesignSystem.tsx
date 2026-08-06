import { useState } from 'react';
import { FileText } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { IconButton } from '@/components/ui/IconButton';
import { Input } from '@/components/ui/Input';
import { SearchInput } from '@/components/ui/SearchInput';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge';
import { MetricCard } from '@/components/ui/MetricCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { Dialog } from '@/components/ui/Dialog';
import { ConfirmationDialog } from '@/components/ui/ConfirmationDialog';
import { useToast } from '@/components/ui/Toast';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';

/** Development-only route (see App.tsx guard) — a living reference for
 * every shared component, so new pages compose from here instead of
 * re-inventing markup. Not shipped in production builds. */
export function DevDesignSystemPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const { showToast } = useToast();

  return (
    <div className="space-y-10 p-6">
      <h1 className="text-2xl font-bold text-text-primary">Design System</h1>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-text-primary">Buttons</h2>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Destructive</Button>
          <Button isLoading>Loading</Button>
          <Button disabled>Disabled</Button>
          <IconButton aria-label="Example icon button">
            <FileText className="h-4 w-4" aria-hidden="true" />
          </IconButton>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-text-primary">Inputs</h2>
        <div className="max-w-sm space-y-3">
          <Input placeholder="Text input" />
          <Input placeholder="Error state" hasError />
          <SearchInput placeholder="Search…" aria-label="Design system search example" />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-text-primary">Badges</h2>
        <div className="flex flex-wrap gap-2">
          <StatusBadge status="processing" />
          <StatusBadge status="approved" />
          <StatusBadge status="needs_review" />
          <StatusBadge status="failed" />
          <ConfidenceBadge score={0.95} />
          <ConfidenceBadge score={0.7} />
          <ConfidenceBadge score={0.3} />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-text-primary">Metric card</h2>
        <div className="max-w-xs">
          <MetricCard label="Documents processed" value="128" trend={{ direction: 'up', label: '12% this week' }} />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-text-primary">Tabs</h2>
        <Tabs defaultValue="one" className="max-w-sm">
          <TabsList>
            <TabsTrigger value="one">One</TabsTrigger>
            <TabsTrigger value="two">Two</TabsTrigger>
          </TabsList>
          <TabsContent value="one" className="p-3 text-sm text-text-secondary">
            Tab one content
          </TabsContent>
          <TabsContent value="two" className="p-3 text-sm text-text-secondary">
            Tab two content
          </TabsContent>
        </Tabs>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-text-primary">States</h2>
        <div className="grid max-w-2xl grid-cols-1 gap-4 sm:grid-cols-2">
          <EmptyState icon={FileText} title="No documents" description="Upload one to get started." />
          <ErrorState onRetry={() => {}} />
        </div>
        <div className="max-w-sm space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-text-primary">Overlays</h2>
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => setDialogOpen(true)}>Open dialog</Button>
          <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
            Open confirmation
          </Button>
          <Button variant="secondary" onClick={() => showToast({ title: 'Saved', variant: 'success' })}>
            Show toast
          </Button>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen} title="Example dialog" description="Focus is trapped inside while open.">
          <Button onClick={() => setDialogOpen(false)}>Close</Button>
        </Dialog>
        <ConfirmationDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          title="Delete document?"
          description="This action cannot be undone."
          isDestructive
          onConfirm={() => setConfirmOpen(false)}
        />
      </section>
    </div>
  );
}
