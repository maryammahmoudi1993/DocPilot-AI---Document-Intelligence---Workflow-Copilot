import { FileText } from 'lucide-react';
import { RoutePlaceholder } from '@/components/layout/RoutePlaceholder';

export function DocumentsPage() {
  return <RoutePlaceholder title="Documents" description="Upload, review, and manage documents in this demo workspace." icon={FileText} />;
}
