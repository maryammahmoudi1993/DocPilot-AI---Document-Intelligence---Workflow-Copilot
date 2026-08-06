import { Menu, User } from 'lucide-react';
import { IconButton } from '@/components/ui/IconButton';
import { SearchInput } from '@/components/ui/SearchInput';

export interface HeaderProps {
  onOpenMobileNav: () => void;
}

/** Workspace selector and authenticated-user menu are placeholders here —
 * they become real in the auth phase, once there's a session to read
 * from. This phase only builds the shell they'll plug into. */
export function Header({ onOpenMobileNav }: HeaderProps) {
  return (
    <header className="sticky top-0 z-sticky flex h-16 items-center gap-3 border-b border-border bg-card px-4">
      <IconButton aria-label="Open navigation menu" onClick={onOpenMobileNav} className="lg:hidden">
        <Menu className="h-5 w-5" aria-hidden="true" />
      </IconButton>

      <div className="max-w-sm flex-1">
        <SearchInput placeholder="Search documents, workflows…" aria-label="Search" />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-soft text-primary">
          <User className="h-4 w-4" aria-hidden="true" />
        </div>
      </div>
    </header>
  );
}
