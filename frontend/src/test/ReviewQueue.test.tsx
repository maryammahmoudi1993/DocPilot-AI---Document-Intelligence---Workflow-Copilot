import { describe, it, expect, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import { extractionQueueHandler } from '@/mocks/extractionHandlers';
import { ReviewQueuePage } from '@/pages/ReviewQueue';
import { renderWithProviders } from '@/test/testUtils';

function renderQueue() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/app/review-queue']}>
      <Routes>
        <Route path="/app/review-queue" element={<ReviewQueuePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  server.use(...signedInHandlers);
});

describe('ReviewQueuePage', () => {
  it('shows an empty state when nothing is pending review', async () => {
    server.use(extractionQueueHandler([]));
    renderQueue();

    expect(await screen.findByText('Nothing waiting on review')).toBeInTheDocument();
  });

  it('lists pending extractions with a confidence badge and links into the review page', async () => {
    server.use(
      extractionQueueHandler([
        {
          id: 'ext-1',
          document_id: 'doc-1',
          filename: 'acme-invoice-0142.pdf',
          document_type: 'invoice',
          status: 'pending_review',
          overall_confidence: 0.42,
          error_issue_count: 1,
          created_at: '2026-08-10T00:00:00Z',
        },
      ]),
    );
    renderQueue();

    expect(await screen.findByText('acme-invoice-0142.pdf')).toBeInTheDocument();
    expect(screen.getByText('1 issue to resolve')).toBeInTheDocument();
    expect(screen.getByText(/Low/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /acme-invoice-0142\.pdf/ })).toHaveAttribute(
      'href',
      '/app/documents/doc-1/review',
    );
  });
});
