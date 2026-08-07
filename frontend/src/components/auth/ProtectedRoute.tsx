import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useSession } from '@/features/auth/hooks';
import { FullPageSpinner } from '@/components/ui/FullPageSpinner';

/**
 * Client-side gating only improves UX (no loading flash of protected
 * content, a clean redirect) — it never replaces server-side
 * enforcement. Every real authorization decision is still made by the
 * backend on every request (see apps/workspaces/permissions.py).
 */
export function ProtectedRoute() {
  const location = useLocation();
  const { data, isLoading, isError } = useSession();

  if (isLoading) {
    return <FullPageSpinner />;
  }

  if (isError || !data) {
    // Preserve where the user was headed so sign-in can return them
    // there instead of always landing on the dashboard.
    return <Navigate to="/sign-in" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
