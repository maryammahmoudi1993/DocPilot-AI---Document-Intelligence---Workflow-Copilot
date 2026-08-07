import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { Drawer } from '@/components/ui/Drawer';
import { useSession } from '@/features/auth/hooks';
import { cn } from '@/lib/utils';

/**
 * Every protected product route renders through this shell (see
 * src/App.tsx) — no page re-implements the sidebar or header. Desktop
 * sidebar collapses in place; below the `lg` breakpoint it moves into a
 * Drawer instead of just hiding, so navigation is never unreachable.
 */
export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const { data: session } = useSession();
  const activeRole = session?.workspaces.find((w) => w.id === session.active_workspace_id)?.role;

  return (
    <div className="flex min-h-screen bg-page">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-toast focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to main content
      </a>

      <aside
        className={cn(
          'hidden shrink-0 border-r border-divider transition-all duration lg:block',
          collapsed ? 'w-16' : 'w-64',
        )}
      >
        <Sidebar
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed((value) => !value)}
          role={activeRole}
        />
      </aside>

      <Drawer open={mobileNavOpen} onOpenChange={setMobileNavOpen} title="DocPilot AI" side="left">
        <Sidebar onNavigate={() => setMobileNavOpen(false)} role={activeRole} />
      </Drawer>

      <div className="flex min-w-0 flex-1 flex-col">
        <Header onOpenMobileNav={() => setMobileNavOpen(true)} />
        <main id="main-content" tabIndex={-1} className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
