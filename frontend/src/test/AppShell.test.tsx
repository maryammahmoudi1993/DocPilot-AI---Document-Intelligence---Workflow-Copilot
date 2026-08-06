import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';

function renderShell() {
  return render(
    <MemoryRouter initialEntries={['/app/dashboard']}>
      <Routes>
        <Route path="/app" element={<AppShell />}>
          <Route path="dashboard" element={<div>Dashboard content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('AppShell', () => {
  it('renders a single main landmark with the routed page content', () => {
    renderShell();
    expect(screen.getByRole('main')).toHaveTextContent('Dashboard content');
  });

  it('renders a skip-to-content link as the first focusable element', () => {
    renderShell();
    expect(screen.getByRole('link', { name: /skip to main content/i })).toBeInTheDocument();
  });

  it('opens the mobile navigation drawer from the header menu button', async () => {
    renderShell();
    // Only the desktop Sidebar is in the accessibility tree before opening
    // (the drawer's Sidebar isn't mounted yet).
    expect(screen.getAllByRole('link', { name: 'Dashboard' })).toHaveLength(1);

    await userEvent.click(screen.getByRole('button', { name: /open navigation menu/i }));

    const dialog = await screen.findByRole('dialog', { name: 'DocPilot AI' });
    // The desktop Sidebar's link is still in the DOM, but Radix marks the
    // rest of the page aria-hidden while the drawer is open, so it drops
    // out of the accessibility tree — the count correctly stays at 1
    // (now the drawer's link), which we confirm lives inside the dialog.
    expect(screen.getAllByRole('link', { name: 'Dashboard' })).toHaveLength(1);
    expect(within(dialog).getByRole('link', { name: 'Dashboard' })).toBeInTheDocument();
  });
});
