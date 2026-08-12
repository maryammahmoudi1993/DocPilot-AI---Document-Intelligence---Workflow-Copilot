import { describe, it, expect, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { config } from '@/config';
import { server } from '@/mocks/server';
import { signedInHandlers, demoWorkspaces } from '@/mocks/handlers';
import { analyticsHandlers, demoAnalyticsOverview } from '@/mocks/analyticsHandlers';
import { AnalyticsPage } from '@/pages/Analytics';
import { renderWithProviders } from '@/test/testUtils';

const API = config.apiBaseUrl;
const WORKSPACE_ID = demoWorkspaces[0]!.id;

function renderAnalytics() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/app/analytics']}>
      <Routes>
        <Route path="/app/analytics" element={<AnalyticsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  server.use(...signedInHandlers, ...analyticsHandlers);
});

describe('AnalyticsPage', () => {
  it('renders computed metrics and labels the illustrative one', async () => {
    renderAnalytics();

    expect(await screen.findByText('87%')).toBeInTheDocument(); // extraction confidence
    expect(screen.getByText('67%')).toBeInTheDocument(); // review rate
    expect(screen.getByText('75%')).toBeInTheDocument(); // workflow success
    expect(screen.getByText('Illustrative metric')).toBeInTheDocument();
  });

  it('renders document type counts', async () => {
    renderAnalytics();

    expect(await screen.findByText('invoice')).toBeInTheDocument();
    expect(screen.getByText('· 6')).toBeInTheDocument();
  });

  it('shows an empty state when there is no processing activity', async () => {
    server.use(
      http.get(`${API}/workspaces/${WORKSPACE_ID}/analytics/`, () =>
        HttpResponse.json({
          ...demoAnalyticsOverview,
          processing_trends: [{ date: '2026-08-12', total: 0, completed: 0, failed: 0 }],
        }),
      ),
    );
    renderAnalytics();

    expect(await screen.findByText(/no processing activity/i)).toBeInTheDocument();
  });

  it('shows an error state with retry', async () => {
    server.use(
      http.get(`${API}/workspaces/${WORKSPACE_ID}/analytics/`, () =>
        HttpResponse.json({ error: { code: 'internal_error', message: 'Broke.', details: null } }, { status: 500 }),
      ),
    );
    renderAnalytics();

    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
