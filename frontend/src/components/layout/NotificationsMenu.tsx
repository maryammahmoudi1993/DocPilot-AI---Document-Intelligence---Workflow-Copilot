import { useEffect, useRef, useState } from 'react';
import { Bell } from 'lucide-react';
import { useSession } from '@/features/auth/hooks';
import { useMarkNotificationRead, useNotifications } from '@/features/notifications/hooks';
import { IconButton } from '@/components/ui/IconButton';
import { Skeleton } from '@/components/ui/Skeleton';
import { cn } from '@/lib/utils';

/** A small anchored dropdown, not a Dialog — no full-screen overlay/focus
 * trap is warranted for a transient notification list, so this is a
 * minimal hand-rolled popover (close on outside click or Escape) rather
 * than reaching for a Radix primitive not otherwise used in this
 * project (see WorkspaceSelector/Dialog for what is). */
export function NotificationsMenu() {
  const { data: session } = useSession();
  const workspaceId = session?.active_workspace_id ?? undefined;
  const notificationsQuery = useNotifications(workspaceId);
  const markRead = useMarkNotificationRead(workspaceId);

  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const notifications = notificationsQuery.data ?? [];
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  useEffect(() => {
    if (!isOpen) return;
    const handlePointerDown = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  return (
    <div ref={containerRef} className="relative">
      <IconButton
        aria-label={unreadCount > 0 ? `Notifications (${unreadCount} unread)` : 'Notifications'}
        aria-expanded={isOpen}
        aria-haspopup="true"
        onClick={() => setIsOpen((open) => !open)}
        className="relative"
      >
        <Bell className="h-4 w-4" aria-hidden="true" />
        {unreadCount > 0 && (
          <span
            aria-hidden="true"
            className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-status-failed px-1 text-[10px] font-medium text-white"
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </IconButton>

      {isOpen && (
        <div
          role="menu"
          aria-label="Notifications"
          className="absolute right-0 z-dropdown mt-2 w-80 rounded-lg border border-border bg-card p-2 shadow-lg"
        >
          {notificationsQuery.isPending && (
            <div className="flex flex-col gap-2 p-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          )}

          {notifications.length === 0 && !notificationsQuery.isPending && (
            <p className="px-2 py-6 text-center text-sm text-text-secondary">
              You're all caught up.
            </p>
          )}

          {notifications.length > 0 && (
            <ul className="flex max-h-96 flex-col gap-1 overflow-y-auto">
              {notifications.map((notification) => (
                <li key={notification.id}>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => !notification.is_read && markRead.mutate(notification.id)}
                    className={cn(
                      'flex w-full flex-col gap-0.5 rounded-md px-3 py-2 text-left transition-colors duration-fast hover:bg-lavender focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                      !notification.is_read && 'bg-primary-soft/40',
                    )}
                  >
                    <span className="flex items-center gap-1.5 text-sm font-medium text-text-primary">
                      {!notification.is_read && (
                        <span
                          className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
                          aria-hidden="true"
                        />
                      )}
                      {notification.title}
                    </span>
                    {notification.body && (
                      <span className="text-xs text-text-secondary">{notification.body}</span>
                    )}
                    <span className="text-[10px] text-text-muted">
                      {new Date(notification.created_at).toLocaleString()}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
