import { NavLink } from 'react-router-dom';
import { ChevronsLeft, ChevronsRight, FileStack } from 'lucide-react';
import { NAV_ITEMS } from '@/config/navigation';
import type { WorkspaceRole } from '@/features/auth/types';
import { IconButton } from '@/components/ui/IconButton';
import { cn } from '@/lib/utils';

export interface SidebarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onNavigate?: () => void;
  className?: string;
  /** Caller's role in the active workspace — undefined while session
   * data hasn't loaded yet. Items with `requiresRole` are hidden until
   * the role is known, not shown-then-yanked once it resolves. */
  role?: WorkspaceRole;
}

/** Rendered both inline (desktop) and inside the mobile Drawer — this is
 * the single source of sidebar markup so no page duplicates it. */
export function Sidebar({ collapsed = false, onToggleCollapse, onNavigate, className, role }: SidebarProps) {
  const visibleItems = NAV_ITEMS.filter((item) => !item.requiresRole || (role && item.requiresRole.includes(role)));

  return (
    <nav aria-label="Primary" className={cn('flex h-full flex-col bg-sidebar', className)}>
      <div className={cn('flex items-center gap-2 px-4 py-5', collapsed && 'justify-center px-2')}>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-white">
          <FileStack className="h-4 w-4" aria-hidden="true" />
        </div>
        {!collapsed && <span className="font-semibold text-text-primary">DocPilot AI</span>}
      </div>

      <ul className="flex-1 space-y-1 px-2">
        {visibleItems.map((item) => (
          <li key={item.path}>
            <NavLink
              to={item.path}
              onClick={onNavigate}
              // When collapsed, the visible label is hidden and the icon
              // is aria-hidden — without this the link would have no
              // accessible name at all for screen-reader users.
              aria-label={collapsed ? item.label : undefined}
              title={collapsed ? item.label : undefined}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-fast',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                  collapsed && 'justify-center px-2',
                  isActive
                    ? 'bg-primary-soft text-primary'
                    : 'text-text-secondary hover:bg-lavender hover:text-text-primary',
                )
              }
            >
              <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          </li>
        ))}
      </ul>

      {onToggleCollapse && (
        <div className="border-t border-divider p-2">
          <IconButton
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            onClick={onToggleCollapse}
            className="w-full"
          >
            {collapsed ? (
              <ChevronsRight className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ChevronsLeft className="h-4 w-4" aria-hidden="true" />
            )}
          </IconButton>
        </div>
      )}
    </nav>
  );
}
