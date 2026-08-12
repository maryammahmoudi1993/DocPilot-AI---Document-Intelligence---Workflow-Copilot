import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { RouteErrorBoundary } from '@/components/RouteErrorBoundary';

function Throws({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('Route render error');
  return <div>Page content</div>;
}

function Harness() {
  const [shouldThrow, setShouldThrow] = useState(true);
  return (
    <div>
      <nav>Sidebar still here</nav>
      <RouteErrorBoundary>
        <Throws shouldThrow={shouldThrow} />
      </RouteErrorBoundary>
      <button onClick={() => setShouldThrow(false)}>Fix the page</button>
    </div>
  );
}

describe('RouteErrorBoundary', () => {
  it('catches a render error and shows a retry action without unmounting siblings', () => {
    render(<Harness />);

    expect(screen.getByText(/couldn't be displayed/i)).toBeInTheDocument();
    expect(screen.getByText('Sidebar still here')).toBeInTheDocument();
  });

  it('retrying re-renders the subtree', async () => {
    const user = userEvent.setup();
    render(<Harness />);

    // Fix the underlying condition first (as a real recovery would —
    // e.g. a refetch resolving), then retry the boundary itself.
    await user.click(screen.getByRole('button', { name: /fix the page/i }));
    await user.click(screen.getByRole('button', { name: /try again/i }));

    expect(screen.getByText('Page content')).toBeInTheDocument();
  });
});
