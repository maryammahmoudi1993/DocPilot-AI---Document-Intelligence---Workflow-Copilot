import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from '@/components/layout/Sidebar';

describe('Sidebar', () => {
  it('marks the current route as the active nav item', () => {
    render(
      <MemoryRouter initialEntries={['/app/documents']}>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: 'Documents' })).toHaveClass('text-primary');
    expect(screen.getByRole('link', { name: 'Dashboard' })).not.toHaveClass('text-primary');
  });

  it('hides nav labels when collapsed but keeps them accessible via the icon-only link name', () => {
    render(
      <MemoryRouter initialEntries={['/app/dashboard']}>
        <Sidebar collapsed />
      </MemoryRouter>,
    );
    // The link itself keeps its accessible name (via aria-label) even
    // though the visible <span> label is not rendered while collapsed.
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument();
  });

  it('calls onToggleCollapse from the collapse control', async () => {
    const onToggleCollapse = vi.fn();
    const { default: userEvent } = await import('@testing-library/user-event');
    render(
      <MemoryRouter>
        <Sidebar onToggleCollapse={onToggleCollapse} />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('button', { name: /collapse sidebar/i }));
    expect(onToggleCollapse).toHaveBeenCalledOnce();
  });

  it('calls onNavigate when a link is clicked (used to close the mobile drawer)', async () => {
    const onNavigate = vi.fn();
    const { default: userEvent } = await import('@testing-library/user-event');
    render(
      <MemoryRouter>
        <Sidebar onNavigate={onNavigate} />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('link', { name: 'Documents' }));
    expect(onNavigate).toHaveBeenCalledOnce();
  });
});
