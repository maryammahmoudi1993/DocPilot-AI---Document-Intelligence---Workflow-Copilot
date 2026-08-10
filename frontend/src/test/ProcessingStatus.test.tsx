import { describe, it, expect, beforeEach } from 'vitest';
import { screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import {
  documentHandlers,
  uploadSuccessHandler,
  processingStatusHandler,
  processingSequenceHandler,
  processingRetryHandler,
} from '@/mocks/documentHandlers';
import { DocumentsPage } from '@/pages/Documents';
import { renderWithProviders } from '@/test/testUtils';

function renderDocuments() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/app/documents']}>
      <Routes>
        <Route path="/app/documents" element={<DocumentsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

async function uploadOneFile(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByText('acme-invoice-0142.pdf');
  await user.click(screen.getByRole('button', { name: 'Upload Document' }));
  const dialog = screen.getByRole('dialog', { name: 'Upload documents' });
  const file = new File(['%PDF-1.4 test'], 'report.pdf', { type: 'application/pdf' });
  await user.upload(within(dialog).getByLabelText(/drag and drop files here/i), file);
  await within(dialog).findByText('report.pdf');
  return dialog;
}

beforeEach(() => {
  server.use(...signedInHandlers, ...documentHandlers, uploadSuccessHandler());
});

describe('Processing status — inline in the upload dialog', () => {
  it('shows a Queued badge right after upload while the job is still queued', async () => {
    server.use(processingStatusHandler({ stage: 'queued' }));
    const user = userEvent.setup();
    renderDocuments();
    const dialog = await uploadOneFile(user);

    expect(await within(dialog).findByText('Queued')).toBeInTheDocument();
  });

  it('shows the current processing stage while the pipeline is running', async () => {
    server.use(processingStatusHandler({ stage: 'running_ocr' }));
    const user = userEvent.setup();
    renderDocuments();
    const dialog = await uploadOneFile(user);

    expect(await within(dialog).findByText('Processing')).toBeInTheDocument();
    expect(within(dialog).getByText('Running OCR')).toBeInTheDocument();
  });

  it('shows a Processed badge once the pipeline completes', async () => {
    server.use(processingStatusHandler({ stage: 'completed' }));
    const user = userEvent.setup();
    renderDocuments();
    const dialog = await uploadOneFile(user);

    expect(await within(dialog).findByText('Processed')).toBeInTheDocument();
  });

  it('shows the safe error message and a retry action when processing fails', async () => {
    server.use(
      processingStatusHandler({
        stage: 'failed',
        is_retryable: true,
        error_message: 'OCR provider unavailable.',
      }),
    );
    const user = userEvent.setup();
    renderDocuments();
    const dialog = await uploadOneFile(user);

    expect(await within(dialog).findByText('Failed')).toBeInTheDocument();
    expect(within(dialog).getByText('OCR provider unavailable.')).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: 'Retry processing' })).toBeInTheDocument();
  });

  it('does not show a retry action for a non-retryable failure', async () => {
    server.use(processingStatusHandler({ stage: 'failed', is_retryable: false }));
    const user = userEvent.setup();
    renderDocuments();
    const dialog = await uploadOneFile(user);

    await within(dialog).findByText('Failed');
    expect(within(dialog).queryByRole('button', { name: 'Retry processing' })).not.toBeInTheDocument();
  });

  it('retrying a failed job updates the status without waiting for the next poll', async () => {
    server.use(
      processingStatusHandler({ stage: 'failed', is_retryable: true, error_message: 'Timed out.' }),
      processingRetryHandler('queued'),
    );
    const user = userEvent.setup();
    renderDocuments();
    const dialog = await uploadOneFile(user);

    await within(dialog).findByText('Failed');
    await user.click(within(dialog).getByRole('button', { name: 'Retry processing' }));

    expect(await within(dialog).findByText('Queued')).toBeInTheDocument();
  });

  it('progresses through stages as it polls, then stops once completed', async () => {
    server.use(processingSequenceHandler(['validating', 'completed']));
    const user = userEvent.setup();
    renderDocuments();
    const dialog = await uploadOneFile(user);

    expect(await within(dialog).findByText('Validating')).toBeInTheDocument();
    expect(
      await within(dialog).findByText('Processed', {}, { timeout: 5000 }),
    ).toBeInTheDocument();

    // No further polling once terminal — the badge stays put.
    await waitFor(() => expect(within(dialog).getByText('Processed')).toBeInTheDocument(), {
      timeout: 2000,
    });
  });
});
