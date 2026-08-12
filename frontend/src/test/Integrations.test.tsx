import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import { notificationHandlers, demoWebhookEndpoints } from '@/mocks/notificationHandlers';
import { IntegrationsPage } from '@/pages/Integrations';
import { renderWithProviders } from '@/test/testUtils';

function renderIntegrations() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/app/integrations']}>
      <Routes>
        <Route path="/app/integrations" element={<IntegrationsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  demoWebhookEndpoints.length = 1;
  demoWebhookEndpoints[0] = {
    id: 'endpoint-1',
    name: 'CRM sync',
    url: 'https://example.com/hooks/docpilot',
    is_active: true,
    is_simulated: true,
    created_at: '2026-08-01T00:00:00Z',
  };
  server.use(...signedInHandlers, ...notificationHandlers);
});

describe('IntegrationsPage', () => {
  it('lists webhook endpoints and labels them as simulated', async () => {
    renderIntegrations();

    expect(await screen.findByText('CRM sync')).toBeInTheDocument();
    expect(screen.getByText('Simulated integration')).toBeInTheDocument();
    expect(screen.queryByText(/secret/i, { selector: 'span' })).not.toBeInTheDocument();
  });

  it('creates a new webhook endpoint and never displays the secret afterwards', async () => {
    const user = userEvent.setup();
    renderIntegrations();
    await screen.findByText('CRM sync');

    await user.click(screen.getByRole('button', { name: /new endpoint/i }));
    await user.type(screen.getByLabelText('Name'), 'Slack alerts');
    await user.type(screen.getByLabelText('URL'), 'https://hooks.slack.com/services/demo');
    await user.type(screen.getByLabelText(/secret/i), 'a-secure-secret');
    await user.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByText('Slack alerts')).toBeInTheDocument();
    expect(screen.queryByText('a-secure-secret')).not.toBeInTheDocument();
  });

  it('deletes an endpoint after confirmation', async () => {
    const user = userEvent.setup();
    renderIntegrations();
    await screen.findByText('CRM sync');

    await user.click(screen.getByRole('button', { name: /delete crm sync/i }));
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(screen.queryByText('CRM sync')).not.toBeInTheDocument());
  });

  it('shows the delivery log for an endpoint', async () => {
    const user = userEvent.setup();
    renderIntegrations();
    await screen.findByText('CRM sync');

    await user.click(screen.getByRole('button', { name: 'Deliveries' }));

    expect(await screen.findByText('document.processed')).toBeInTheDocument();
    expect(screen.getByText('succeeded')).toBeInTheDocument();
  });
});
