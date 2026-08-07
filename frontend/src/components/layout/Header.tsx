import { LogOut, Menu, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { IconButton } from '@/components/ui/IconButton';
import { SearchInput } from '@/components/ui/SearchInput';
import { WorkspaceSelector } from './WorkspaceSelector';
import { useLogout, useSession } from '@/features/auth/hooks';

export interface HeaderProps {
  onOpenMobileNav: () => void;
}

export function Header({ onOpenMobileNav }: HeaderProps) {
  const navigate = useNavigate();
  const { data: session } = useSession();
  const logout = useLogout();

  const handleLogout = () => {
    logout.mutate(undefined, {
      onSettled: () => navigate('/sign-in', { replace: true }),
    });
  };

  return (
    <header className="sticky top-0 z-sticky flex h-16 items-center gap-3 border-b border-border bg-card px-4">
      <IconButton aria-label="Open navigation menu" onClick={onOpenMobileNav} className="lg:hidden">
        <Menu className="h-5 w-5" aria-hidden="true" />
      </IconButton>

      <div className="max-w-sm flex-1">
        <SearchInput placeholder="Search documents, workflows…" aria-label="Search" />
      </div>

      <div className="ml-auto flex items-center gap-3">
        <WorkspaceSelector />

        {session?.user && (
          <span className="hidden text-sm text-text-secondary sm:inline" title={session.user.email}>
            {session.user.email}
          </span>
        )}

        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-soft text-primary">
          <User className="h-4 w-4" aria-hidden="true" />
        </div>

        <IconButton aria-label="Sign out" onClick={handleLogout} disabled={logout.isPending}>
          <LogOut className="h-4 w-4" aria-hidden="true" />
        </IconButton>
      </div>
    </header>
  );
}
