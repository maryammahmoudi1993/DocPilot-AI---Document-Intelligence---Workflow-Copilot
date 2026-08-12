import { describe, it, expect, beforeEach } from 'vitest';
import { axe } from 'jest-axe';
import { screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import { documentHandlers } from '@/mocks/documentHandlers';
import { analyticsHandlers } from '@/mocks/analyticsHandlers';
import { approvalHandlers } from '@/mocks/approvalHandlers';
import { workspaceSettingsHandlers } from '@/mocks/workspaceSettingsHandlers';
import { Home } from '@/pages/Home';
import { SignInPage } from '@/pages/SignIn';
import { DashboardPage } from '@/pages/Dashboard';
import { ApprovalsPage } from '@/pages/Approvals';
import { SettingsPage } from '@/pages/Settings';
import { renderWithProviders } from '@/test/testUtils';

/** Automated axe-core scans for serious/critical violations — a floor,
 * not the whole accessibility story (see the manually-authored
 * keyboard/focus specs elsewhere, e.g. e2e/sign-in.spec.ts). Each page
 * is awaited to a populated, non-loading state before scanning, since
 * a skeleton-only scan under-tests the real page. */
function renderRoute(path: string, element: React.ReactElement) {
  return renderWithProviders(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path={path} element={element} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  server.use(
    ...signedInHandlers,
    ...documentHandlers,
    ...analyticsHandlers,
    ...approvalHandlers,
    ...workspaceSettingsHandlers,
  );
});

describe('Automated accessibility scan (axe) — no serious/critical violations', () => {
  it('Landing page', async () => {
    const { container } = renderRoute('/', <Home />);
    await screen.findByRole('heading', { level: 1 });
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Sign in page', async () => {
    const { container } = renderRoute('/sign-in', <SignInPage />);
    await screen.findByRole('heading', { name: 'Welcome back' });
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Dashboard page', async () => {
    const { container } = renderRoute('/app/dashboard', <DashboardPage />);
    await screen.findByText('Recent documents');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Approvals page', async () => {
    const { container } = renderRoute('/app/approvals', <ApprovalsPage />);
    await screen.findByText('Invoice over $10,000 threshold');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Settings page', async () => {
    const { container } = renderRoute('/app/settings', <SettingsPage />);
    await screen.findByText('Notifications');
    expect(await axe(container)).toHaveNoViolations();
  });
});
