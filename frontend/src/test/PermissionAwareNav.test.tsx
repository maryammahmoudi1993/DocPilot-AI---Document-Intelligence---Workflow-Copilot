import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from '@/components/layout/Sidebar';
import { renderWithProviders } from '@/test/testUtils';

function renderSidebar(role?: 'owner' | 'admin' | 'finance_manager' | 'reviewer' | 'viewer') {
  return renderWithProviders(
    <MemoryRouter>
      <Sidebar role={role} />
    </MemoryRouter>,
  );
}

describe('Sidebar — permission-aware navigation', () => {
  it('hides Settings until the role is known (avoids a show-then-hide flash)', () => {
    renderSidebar(undefined);
    expect(screen.queryByRole('link', { name: 'Settings' })).not.toBeInTheDocument();
  });

  it('hides Settings for a Viewer', () => {
    renderSidebar('viewer');
    expect(screen.queryByRole('link', { name: 'Settings' })).not.toBeInTheDocument();
  });

  it('hides Settings for a Reviewer', () => {
    renderSidebar('reviewer');
    expect(screen.queryByRole('link', { name: 'Settings' })).not.toBeInTheDocument();
  });

  it('hides Settings for a Finance Manager', () => {
    renderSidebar('finance_manager');
    expect(screen.queryByRole('link', { name: 'Settings' })).not.toBeInTheDocument();
  });

  it('shows Settings for an Admin', () => {
    renderSidebar('admin');
    expect(screen.getByRole('link', { name: 'Settings' })).toBeInTheDocument();
  });

  it('shows Settings for the Owner', () => {
    renderSidebar('owner');
    expect(screen.getByRole('link', { name: 'Settings' })).toBeInTheDocument();
  });

  it('always shows non-restricted items regardless of role', () => {
    renderSidebar('viewer');
    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Documents' })).toBeInTheDocument();
  });
});
