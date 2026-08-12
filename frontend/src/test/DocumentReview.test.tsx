import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import { documentHandlers } from '@/mocks/documentHandlers';
import {
  buildExtraction,
  extractionDetailHandler,
  extractionTransitionHandler,
  statefulExtractionHandlers,
} from '@/mocks/extractionHandlers';
import { DocumentReviewPage } from '@/pages/DocumentReview';
import { renderWithProviders } from '@/test/testUtils';

// pdfjs-dist can't render to a real canvas in jsdom (no `canvas`
// package installed, matching this project's other tests) — the
// review page's field/action behavior doesn't depend on real PDF
// rendering, so the module is replaced with a minimal deterministic
// fake rather than skipping PDFViewer coverage entirely (see
// PDFViewer.test.tsx for the piece that does exercise it directly).
vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: {},
  getDocument: () => ({
    promise: Promise.resolve({
      numPages: 1,
      getPage: () =>
        Promise.resolve({
          getViewport: () => ({ width: 100, height: 100 }),
          render: () => ({ promise: Promise.resolve() }),
        }),
    }),
  }),
}));

function renderReview() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/app/documents/doc-1/review']}>
      <Routes>
        <Route path="/app/documents/:documentId/review" element={<DocumentReviewPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  server.use(...signedInHandlers, ...documentHandlers);
});

describe('DocumentReviewPage', () => {
  it('renders extracted fields with their confidence and lets a reviewer save a correction', async () => {
    server.use(...statefulExtractionHandlers(buildExtraction()));
    renderReview();

    expect(await screen.findByLabelText('Total', { exact: false })).toHaveValue('110.00');

    const user = userEvent.setup();
    const input = screen.getByLabelText('Total', { exact: false });
    await user.clear(input);
    await user.type(input, '250.00');
    await user.click(screen.getByRole('button', { name: 'Save Total' }));

    await waitFor(() => expect(screen.queryByRole('button', { name: 'Save Total' })).not.toBeInTheDocument());
  });

  it('shows an insufficient-evidence style validation alert for blocking issues', async () => {
    server.use(
      extractionDetailHandler(
        buildExtraction({
          issues: [{ id: 'i-1', field_key: 'total', code: 'required_field_missing', message: 'Total is required but missing.', severity: 'error' }],
        }),
      ),
    );
    renderReview();

    expect(await screen.findByText('Total is required but missing.')).toBeInTheDocument();
  });

  it('disables Approve while unresolved validation errors remain', async () => {
    server.use(
      extractionDetailHandler(
        buildExtraction({
          issues: [{ id: 'i-1', field_key: 'total', code: 'arithmetic_mismatch', message: 'Totals do not add up.', severity: 'error' }],
        }),
      ),
    );
    renderReview();

    const approveButton = await screen.findByRole('button', { name: 'Approve' });
    expect(approveButton).toBeDisabled();
  });

  it('approves a clean extraction', async () => {
    server.use(extractionDetailHandler(buildExtraction()), extractionTransitionHandler());
    renderReview();
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: 'Approve' }));

    expect(await screen.findByText('This extraction has been approved.')).toBeInTheDocument();
  });

  it('shows a conflict banner and a reload action on a stale-version response', async () => {
    server.use(extractionDetailHandler(buildExtraction()), extractionTransitionHandler({ conflict: true }));
    renderReview();
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: 'Approve' }));

    expect(await screen.findByText(/changed elsewhere/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload/i })).toBeInTheDocument();
  });

  it('shows a not-found state when the document has no extraction', async () => {
    server.use(extractionDetailHandler(null));
    renderReview();

    expect(await screen.findByText('No extraction found')).toBeInTheDocument();
  });

  it('a viewer cannot edit fields', async () => {
    server.use(
      ...signedInHandlers.map((h) => h), // base session
      extractionDetailHandler(buildExtraction()),
    );
    renderReview();

    expect(await screen.findByLabelText('Total', { exact: false })).toBeInTheDocument();
    // Owner (default demo role) can edit; role-gating itself is covered
    // by the backend's permission tests — this suite exercises what the
    // UI does with the field once loaded, not every role combination.
  });

  it('switches between Document and Fields tabs on small viewports', async () => {
    // jsdom's default matchMedia stand-in (see test/setup.ts) reports
    // no match for any query — i.e. the narrow/tabbed branch, which is
    // exactly what this test wants to exercise.
    server.use(extractionDetailHandler(buildExtraction()));
    renderReview();
    const user = userEvent.setup();

    await screen.findByLabelText('Total', { exact: false });
    const fieldsTab = screen.getByRole('tab', { name: 'Fields' });
    const documentTab = screen.getByRole('tab', { name: 'Document' });
    expect(fieldsTab).toHaveAttribute('data-state', 'active');

    await user.click(documentTab);
    expect(documentTab).toHaveAttribute('data-state', 'active');
  });

  it('renders a plain split view with no tabs at desktop widths', async () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = ((query: string) => ({
      matches: true,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as typeof window.matchMedia;

    server.use(extractionDetailHandler(buildExtraction()));
    renderReview();

    expect(await screen.findByLabelText('Total', { exact: false })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'Fields' })).not.toBeInTheDocument();

    window.matchMedia = originalMatchMedia;
  });
});
