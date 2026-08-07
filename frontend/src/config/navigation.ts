import {
  LayoutDashboard,
  FileText,
  ClipboardCheck,
  Sparkles,
  Workflow,
  CheckSquare,
  BarChart3,
  History,
  Plug,
  Settings,
  type LucideIcon,
} from 'lucide-react';

import { MANAGER_ROLES, type WorkspaceRole } from '@/features/auth/types';

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  /** Omitted = visible to every workspace member. Set = visible only to
   * the listed roles (permission-aware nav — see Sidebar.tsx). This is a
   * UX affordance only; the backend independently enforces who can
   * actually do anything on the page itself. */
  requiresRole?: WorkspaceRole[];
}

/** Single source of truth for the product sidebar — every protected route
 * renders through AppShell/Sidebar using this list, so no page hand-rolls
 * its own navigation. */
export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: '/app/dashboard', icon: LayoutDashboard },
  { label: 'Documents', path: '/app/documents', icon: FileText },
  { label: 'Review Queue', path: '/app/review-queue', icon: ClipboardCheck },
  { label: 'AI Assistant', path: '/app/assistant', icon: Sparkles },
  { label: 'Workflow Builder', path: '/app/workflows', icon: Workflow },
  { label: 'Approvals', path: '/app/approvals', icon: CheckSquare },
  { label: 'Analytics', path: '/app/analytics', icon: BarChart3 },
  { label: 'Audit Log', path: '/app/audit-log', icon: History },
  { label: 'Integrations', path: '/app/integrations', icon: Plug },
  { label: 'Settings', path: '/app/settings', icon: Settings, requiresRole: MANAGER_ROLES },
];
