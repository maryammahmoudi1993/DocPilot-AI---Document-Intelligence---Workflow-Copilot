import { ClipboardCheck } from 'lucide-react';
import { RoutePlaceholder } from '@/components/layout/RoutePlaceholder';

export function ReviewQueuePage() {
  return <RoutePlaceholder title="Review Queue" description="Documents awaiting human review and correction." icon={ClipboardCheck} />;
}
