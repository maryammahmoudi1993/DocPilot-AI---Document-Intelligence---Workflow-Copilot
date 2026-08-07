import { Navigate, Outlet } from 'react-router-dom';
import { useSession } from '@/features/auth/hooks';
import type { WorkspaceRole } from '@/features/auth/types';
import { FullPageSpinner } from '@/components/ui/FullPageSpinner';

export interface RequireRoleProps {
  allowedRoles: WorkspaceRole[];
}

/** Renders its child route only if the caller's role in the active
 * workspace is in `allowedRoles` — UX gating only (see ProtectedRoute's
 * docstring); the backend independently enforces this on every request
 * that actually matters. */
export function RequireRole({ allowedRoles }: RequireRoleProps) {
  const { data, isLoading } = useSession();

  if (isLoading) {
    return <FullPageSpinner />;
  }

  const activeWorkspace = data?.workspaces.find((w) => w.id === data.active_workspace_id);
  const role = activeWorkspace?.role;

  if (!role || !allowedRoles.includes(role)) {
    return <Navigate to="/access-denied" replace />;
  }

  return <Outlet />;
}
