import { describe, it, expect, beforeEach } from 'vitest';
import { screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse, delay } from 'msw';
import { config } from '@/config';
import { server } from '@/mocks/server';
import { signedInHandlers, demoWorkspaces } from '@/mocks/handlers';
import { demoDocuments, documentHandlers, uploadSuccessHandler, uploadErrorHandler } from '@/mocks/documentHandlers';
import { DocumentsPage } from '@/pages/Documents';
import { renderWithProviders } from '@/test/testUtils';

const API = config.apiBaseUrl;
const WORKSPACE_ID = demoWorkspaces[0]!.id;

function renderDocuments(initialPath = '/app/documents') {
  return renderWithProviders(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/app/documents" element={<DocumentsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  server.use(...signedInHandlers, ...documentHandlers);
});

describe('DocumentsPage — list states', () => {
  it('shows a loading state before documents arrive', async () => {
    server.use(
      http.get(`${API}/workspaces/${WORKSPACE_ID}/documents/`, async () => {
        await delay(50);
        return HttpResponse.json({ count: demoDocuments.length, next: null, previous: null, results: demoDocuments });
      }),
    );
    renderDocuments();

    expect(screen.getAllByRole('status').length).toBeGreaterThan(0);
    expect(await screen.findByText('acme-invoice-0142.pdf')).toBeInTheDocument();
  });

  it('renders the document list with filename, status, and owner', async () => {
    renderDocuments();

    expect(await screen.findByText('acme-invoice-0142.pdf')).toBeInTheDocument();
    expect(screen.getByText('vendor-contract-2026.docx')).toBeInTheDocument();
    expect(screen.getByText('Uploaded')).toBeInTheDocument();
    expect(screen.getByText('Archived')).toBeInTheDocument();
  });

  it('shows an empty state when the workspace has no documents', async () => {
    server.use(
      http.get(`${API}/workspaces/${WORKSPACE_ID}/documents/`, () =>
        HttpResponse.json({ count: 0, next: null, previous: null, results: [] }),
      ),
    );
    renderDocuments();

    expect(await screen.findByText(/no documents/i)).toBeInTheDocument();
  });

  it('shows an error state with a retry action when the list request fails', async () => {
    server.use(
      http.get(`${API}/workspaces/${WORKSPACE_ID}/documents/`, () =>
        HttpResponse.json({ error: { code: 'internal_error', message: 'Something broke.', details: null } }, { status: 500 }),
      ),
    );
    const user = userEvent.setup();
    renderDocuments();

    expect(await screen.findByRole('alert')).toBeInTheDocument();

    server.use(
      http.get(`${API}/workspaces/${WORKSPACE_ID}/documents/`, () =>
        HttpResponse.json({ count: demoDocuments.length, next: null, previous: null, results: demoDocuments }),
      ),
    );
    await user.click(screen.getByRole('button', { name: /try again/i }));

    expect(await screen.findByText('acme-invoice-0142.pdf')).toBeInTheDocument();
  });
});

describe('DocumentsPage — search and filters', () => {
  it('filters the list by search text', async () => {
    const user = userEvent.setup();
    renderDocuments();
    await screen.findByText('acme-invoice-0142.pdf');

    await user.type(screen.getByRole('searchbox', { name: /search documents/i }), 'vendor-contract');

    await waitFor(
      () => {
        expect(screen.queryByText('acme-invoice-0142.pdf')).not.toBeInTheDocument();
        expect(screen.getByText('vendor-contract-2026.docx')).toBeInTheDocument();
      },
      { timeout: 2000 },
    );
  });

  it('filters the list by status', async () => {
    const user = userEvent.setup();
    renderDocuments();
    await screen.findByText('acme-invoice-0142.pdf');

    await user.click(screen.getByRole('combobox', { name: /status/i }));
    await user.click(screen.getByRole('option', { name: 'Archived' }));

    await waitFor(() => {
      expect(screen.queryByText('acme-invoice-0142.pdf')).not.toBeInTheDocument();
      expect(screen.getByText('vendor-contract-2026.docx')).toBeInTheDocument();
    });
  });
});

describe('DocumentsPage — upload', () => {
  it('opens the upload dialog from the toolbar button', async () => {
    const user = userEvent.setup();
    renderDocuments();
    await screen.findByText('acme-invoice-0142.pdf');

    await user.click(screen.getByRole('button', { name: 'Upload Document' }));

    expect(screen.getByRole('dialog', { name: 'Upload documents' })).toBeInTheDocument();
  });

  it('uploads a selected file and shows it succeed', async () => {
    server.use(uploadSuccessHandler());
    const user = userEvent.setup();
    renderDocuments();
    await screen.findByText('acme-invoice-0142.pdf');

    await user.click(screen.getByRole('button', { name: 'Upload Document' }));
    const dialog = screen.getByRole('dialog', { name: 'Upload documents' });
    const file = new File(['%PDF-1.4 test content'], 'report.pdf', { type: 'application/pdf' });
    await user.upload(within(dialog).getByLabelText(/drag and drop files here/i), file);

    expect(await within(dialog).findByText('report.pdf')).toBeInTheDocument();
    await waitFor(() => expect(within(dialog).getByText(/uploaded/i)).toBeInTheDocument());
  });

  it('surfaces a validation error and allows retrying the same file', async () => {
    server.use(uploadErrorHandler('validation_error', "Files with extension '.exe' are not allowed.", { file: "Files with extension '.exe' are not allowed." }));
    const user = userEvent.setup();
    renderDocuments();
    await screen.findByText('acme-invoice-0142.pdf');

    await user.click(screen.getByRole('button', { name: 'Upload Document' }));
    const dialog = screen.getByRole('dialog', { name: 'Upload documents' });
    const file = new File(['bad'], 'malware.exe', { type: 'application/octet-stream' });
    await user.upload(within(dialog).getByLabelText(/drag and drop files here/i), file);

    expect(await within(dialog).findByText(/not allowed/i)).toBeInTheDocument();

    server.use(uploadSuccessHandler());
    await user.click(within(dialog).getByRole('button', { name: /retry upload of malware.exe/i }));

    await waitFor(() => expect(within(dialog).getByText(/uploaded/i)).toBeInTheDocument());
  });

  it('surfaces the duplicate-checksum error distinctly', async () => {
    server.use(
      uploadErrorHandler('validation_error', 'A document with identical content already exists in this workspace.', {
        file: 'A document with identical content already exists in this workspace.',
        existing_document_id: 'doc-1',
      }),
    );
    const user = userEvent.setup();
    renderDocuments();
    await screen.findByText('acme-invoice-0142.pdf');

    await user.click(screen.getByRole('button', { name: 'Upload Document' }));
    const dialog = screen.getByRole('dialog', { name: 'Upload documents' });
    const file = new File(['dup'], 'duplicate.pdf', { type: 'application/pdf' });
    await user.upload(within(dialog).getByLabelText(/drag and drop files here/i), file);

    expect(await within(dialog).findByText(/already exists in this workspace/i)).toBeInTheDocument();
  });
});

describe('DocumentsPage — selection and bulk actions', () => {
  it('shows a bulk action bar once rows are selected and archives them', async () => {
    const user = userEvent.setup();
    renderDocuments();
    await screen.findByText('acme-invoice-0142.pdf');

    await user.click(screen.getByRole('checkbox', { name: /select acme-invoice-0142\.pdf/i }));

    expect(await screen.findByText(/1 document selected/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /^archive$/i }));
    const dialog = await screen.findByRole('dialog', { name: /archive selected documents/i });
    await user.click(within(dialog).getByRole('button', { name: /^confirm$/i }));

    await waitFor(() => expect(screen.queryByText(/1 document selected/i)).not.toBeInTheDocument());
  });

  it('deletes selected documents after confirmation', async () => {
    const user = userEvent.setup();
    renderDocuments();
    await screen.findByText('vendor-contract-2026.docx');

    await user.click(screen.getByRole('checkbox', { name: /select vendor-contract-2026\.docx/i }));
    await user.click(screen.getByRole('button', { name: /^delete$/i }));
    const dialog = await screen.findByRole('dialog', { name: /delete selected documents/i });
    await user.click(within(dialog).getByRole('button', { name: /^delete$/i }));

    await waitFor(() => expect(screen.queryByText(/1 document selected/i)).not.toBeInTheDocument());
  });
});

describe('DocumentsPage — accessibility', () => {
  it('has an accessible table name and headers', async () => {
    renderDocuments();
    await screen.findByText('acme-invoice-0142.pdf');

    expect(screen.getByRole('table', { name: /documents/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /name/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /status/i })).toBeInTheDocument();
  });

  it('opens the upload dialog with the dropzone immediately keyboard-focused', async () => {
    const user = userEvent.setup();
    renderDocuments();
    await screen.findByText('acme-invoice-0142.pdf');

    await user.click(screen.getByRole('button', { name: 'Upload Document' }));

    await waitFor(() =>
      expect(within(screen.getByRole('dialog')).getByLabelText(/drag and drop files here/i)).toHaveFocus(),
    );
  });
});
