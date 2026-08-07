import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '@/App';
import { NAV_ITEMS } from '@/config/navigation';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';

// App owns its own BrowserRouter (see App.tsx), so tests navigate via
// real history.pushState rather than wrapping in a second (Memory)
// router — nesting routers would make the inner one win and ignore
// whatever path the outer one was given.
function renderAt(path: string) {
  window.history.pushState({}, '', path);
  return render(<App />);
}

beforeEach(() => {
  // Every /app/* route is now protected (Phase 2B) — sign in first so
  // these route-placeholder checks exercise the shell, not the redirect.
  server.use(...signedInHandlers);
});

afterEach(() => {
  window.history.pushState({}, '', '/');
});

describe('product route placeholders', () => {
  it.each(NAV_ITEMS)('renders the $label route through the shared AppShell', async ({ path, label }) => {
    renderAt(path);
    // The shell (sidebar nav item) and the page heading both exist —
    // proof the route renders through AppShell rather than standalone.
    expect((await screen.findAllByText(label)).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('redirects /app to the dashboard', async () => {
    renderAt('/app');
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
  });
});
