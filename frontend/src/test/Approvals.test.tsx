import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import { approvalHandlers, demoApprovals } from '@/mocks/approvalHandlers';
import { ApprovalsPage } from '@/pages/Approvals';
import { renderWithProviders } from '@/test/testUtils';

function renderApprovals() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/app/approvals']}>
      <Routes>
        <Route path="/app/approvals" element={<ApprovalsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  // Reset the pending demo approval's decision state so tests don't leak
  // into each other via the shared mutable fixture array.
  demoApprovals[0]!.status = 'pending';
  demoApprovals[0]!.decided_by_email = null;
  demoApprovals[0]!.comments = [];
  server.use(...signedInHandlers, ...approvalHandlers);
});

describe('ApprovalsPage', () => {
  it('lists approval requests with risk and status', async () => {
    renderApprovals();

    expect(await screen.findByText('Invoice over $10,000 threshold')).toBeInTheDocument();
    expect(screen.getByText('Contract renewal — Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('high')).toBeInTheDocument();
  });

  it('opens the detail dialog and approves a pending request after confirmation', async () => {
    const user = userEvent.setup();
    renderApprovals();
    await user.click(await screen.findByText('Invoice over $10,000 threshold'));

    await user.click(await screen.findByRole('button', { name: 'Approve' }));
    await user.click(await screen.findByRole('button', { name: 'Approve' }));

    await waitFor(() => expect(demoApprovals[0]!.status).toBe('approved'));
  });

  it('rejects a request with a reason recorded as a comment', async () => {
    const user = userEvent.setup();
    renderApprovals();
    await user.click(await screen.findByText('Invoice over $10,000 threshold'));

    await user.type(screen.getByLabelText(/reason/i), 'Missing vendor documentation');
    await user.click(screen.getByRole('button', { name: 'Reject' }));
    await user.click(await screen.findByRole('button', { name: 'Reject' }));

    await waitFor(() => expect(demoApprovals[0]!.status).toBe('rejected'));
    expect(demoApprovals[0]!.comments.some((c) => c.body === 'Missing vendor documentation')).toBe(
      true,
    );
  });

  it('filters the list by status', async () => {
    const user = userEvent.setup();
    renderApprovals();
    await screen.findByText('Invoice over $10,000 threshold');

    await user.click(screen.getByRole('combobox', { name: /filter by status/i }));
    await user.click(await screen.findByRole('option', { name: 'Approved' }));

    await waitFor(() => {
      expect(screen.queryByText('Invoice over $10,000 threshold')).not.toBeInTheDocument();
      expect(screen.getByText('Contract renewal — Acme Corp')).toBeInTheDocument();
    });
  });
});
