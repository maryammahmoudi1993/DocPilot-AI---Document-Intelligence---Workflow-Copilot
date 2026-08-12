import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PDFViewer } from '@/components/extraction/PDFViewer';
import { renderWithProviders } from '@/test/testUtils';

const getPage = vi.fn(() =>
  Promise.resolve({
    getViewport: () => ({ width: 100, height: 100 }),
    render: () => ({ promise: Promise.resolve() }),
  }),
);

vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: {},
  getDocument: () => ({
    promise: Promise.resolve({ numPages: 3, getPage }),
  }),
}));

describe('PDFViewer', () => {
  it('shows the page count and disables Previous on the first page', async () => {
    renderWithProviders(<PDFViewer fileUrl="https://example.com/doc.pdf" />);

    await waitFor(() => expect(screen.getByText('1 / 3')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Previous page' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Next page' })).toBeEnabled();
  });

  it('navigates to the next page', async () => {
    const user = userEvent.setup();
    renderWithProviders(<PDFViewer fileUrl="https://example.com/doc.pdf" />);
    await waitFor(() => expect(screen.getByText('1 / 3')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: 'Next page' }));

    await waitFor(() => expect(screen.getByText('2 / 3')).toBeInTheDocument());
  });

  it('zooms in and out within bounds', async () => {
    const user = userEvent.setup();
    renderWithProviders(<PDFViewer fileUrl="https://example.com/doc.pdf" />);
    await waitFor(() => expect(screen.getByText('1 / 3')).toBeInTheDocument());

    expect(screen.getByText('100%')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Zoom in' }));
    expect(screen.getByText('125%')).toBeInTheDocument();
    // 125% -> 100% -> 75% -> 50% (clamped at MIN_SCALE).
    await user.click(screen.getByRole('button', { name: 'Zoom out' }));
    await user.click(screen.getByRole('button', { name: 'Zoom out' }));
    await user.click(screen.getByRole('button', { name: 'Zoom out' }));
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Zoom out' })).toBeDisabled();
  });

  it('jumps to the highlighted field page when a highlight is provided', async () => {
    renderWithProviders(
      <PDFViewer fileUrl="https://example.com/doc.pdf" highlight={{ page: 3, box: { x: 0.1, y: 0.1, width: 0.2, height: 0.1 } }} />,
    );

    await waitFor(() => expect(screen.getByText('3 / 3')).toBeInTheDocument());
  });

  it('shows a friendly error state when the document fails to load', async () => {
    vi.mocked(getPage).mockRejectedValueOnce(new Error('boom'));
    // Force getDocument itself to reject for this one test.
    const pdfjs = await import('pdfjs-dist');
    vi.spyOn(pdfjs, 'getDocument').mockImplementationOnce(
      () => ({ promise: Promise.reject(new Error('failed')) }) as ReturnType<typeof pdfjs.getDocument>,
    );

    renderWithProviders(<PDFViewer fileUrl="https://example.com/broken.pdf" />);

    expect(await screen.findByText('The document preview could not be loaded.')).toBeInTheDocument();
  });
});
