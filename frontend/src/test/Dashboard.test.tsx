import { describe, it, expect, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import { demoDocuments, documentHandlers } from '@/mocks/documentHandlers';
import { analyticsHandlers, demoDashboardSummary } from '@/mocks/analyticsHandlers';
import { DashboardPage } from '@/pages/Dashboard';
import { renderWithProviders } from '@/test/testUtils';

function renderDashboard() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/app/dashboard']}>
      <Routes>
        <Route path="/app/dashboard" element={<DashboardPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  server.use(...signedInHandlers, ...documentHandlers, ...analyticsHandlers);
});

describe('DashboardPage', () => {
  it('renders real summary counts from the API, not sample placeholders', async () => {
    renderDashboard();

    expect(await screen.findByText(String(demoDashboardSummary.total_documents))).toBeInTheDocument();
    expect(screen.getByText(String(demoDashboardSummary.pending_approvals))).toBeInTheDocument();
    expect(screen.queryByText('Illustrative metric')).not.toBeInTheDocument();
  });

  it('lists recent documents', async () => {
    renderDashboard();

    expect(await screen.findByText(demoDocuments[0]!.filename)).toBeInTheDocument();
  });
});
