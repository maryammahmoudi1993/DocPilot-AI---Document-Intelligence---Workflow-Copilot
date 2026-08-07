import { ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { EmptyState } from '@/components/ui/EmptyState';
import { Button } from '@/components/ui/Button';

export function AccessDeniedPage() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center bg-page p-6">
      <EmptyState
        icon={ShieldAlert}
        title="You don't have access to this page"
        description="Your role in this workspace doesn't include this. If you think that's wrong, ask a workspace owner or admin."
        action={
          <Button variant="secondary" onClick={() => navigate('/app/dashboard')}>
            Back to dashboard
          </Button>
        }
      />
    </div>
  );
}
