import { describe, it, expect, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import { auditHandlers } from '@/mocks/auditHandlers';
import { AuditLogPage } from '@/pages/AuditLog';
import { renderWithProviders } from '@/test/testUtils';

function renderAuditLog() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/app/audit-log']}>
      <Routes>
        <Route path="/app/audit-log" element={<AuditLogPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  server.use(...signedInHandlers, ...auditHandlers);
});

describe('AuditLogPage', () => {
  it('lists audit events with actor and timestamp', async () => {
    renderAuditLog();

    expect(await screen.findByText('approval.approved')).toBeInTheDocument();
    expect(screen.getByText('document.uploaded')).toBeInTheDocument();
  });

  it('expands an event to show its metadata as JSON', async () => {
    const user = userEvent.setup();
    renderAuditLog();
    await screen.findByText('approval.approved');

    await user.click(screen.getByText('approval.approved'));

    expect(await screen.findByText(/"approval_id"/)).toBeInTheDocument();
  });

  it('filters by event type', async () => {
    const user = userEvent.setup();
    renderAuditLog();
    await screen.findByText('approval.approved');

    await user.type(screen.getByLabelText(/event type/i), 'document.uploaded');

    expect(await screen.findByText('document.uploaded')).toBeInTheDocument();
    expect(screen.queryByText('approval.approved')).not.toBeInTheDocument();
  });
});
