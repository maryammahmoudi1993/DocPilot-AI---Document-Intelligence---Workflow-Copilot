import { History } from 'lucide-react';
import { RoutePlaceholder } from '@/components/layout/RoutePlaceholder';

export function AuditLogPage() {
  return <RoutePlaceholder title="Audit Log" description="Immutable record of workspace activity." icon={History} />;
}
