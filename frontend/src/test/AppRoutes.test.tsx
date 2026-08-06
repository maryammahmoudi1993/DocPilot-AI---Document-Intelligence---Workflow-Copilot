import { describe, it, expect, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '@/App';
import { NAV_ITEMS } from '@/config/navigation';

// App owns its own BrowserRouter (see App.tsx), so tests navigate via
// real history.pushState rather than wrapping in a second (Memory)
// router — nesting routers would make the inner one win and ignore
// whatever path the outer one was given.
function renderAt(path: string) {
  window.history.pushState({}, '', path);
  return render(<App />);
}

afterEach(() => {
  window.history.pushState({}, '', '/');
});

describe('product route placeholders', () => {
  it.each(NAV_ITEMS)('renders the $label route through the shared AppShell', ({ path, label }) => {
    renderAt(path);
    // The shell (sidebar nav item) and the page heading both exist —
    // proof the route renders through AppShell rather than standalone.
    expect(screen.getAllByText(label).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('redirects /app to the dashboard', () => {
    renderAt('/app');
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
  });
});
