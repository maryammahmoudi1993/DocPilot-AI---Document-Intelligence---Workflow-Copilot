import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import { demoWorkspaceSettings, workspaceSettingsHandlers } from '@/mocks/workspaceSettingsHandlers';
import { SettingsPage } from '@/pages/Settings';
import { renderWithProviders } from '@/test/testUtils';

function renderSettings() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/app/settings']}>
      <Routes>
        <Route path="/app/settings" element={<SettingsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  Object.assign(demoWorkspaceSettings, {
    notify_on_approval_requested: true,
    notify_on_document_processed: true,
    webhook_notifications_enabled: true,
    auto_classify_enabled: true,
    document_retention_days: null,
    raw_text_retention_days: null,
  });
  server.use(...signedInHandlers, ...workspaceSettingsHandlers);
});

describe('SettingsPage', () => {
  it('renders the current settings', async () => {
    renderSettings();

    expect(await screen.findByText('Notifications')).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: /notify on approval requested/i })).toBeChecked();
  });

  it('toggling a preference and saving persists the change', async () => {
    const user = userEvent.setup();
    renderSettings();
    await screen.findByText('Notifications');

    await user.click(screen.getByRole('switch', { name: /auto-classify uploaded documents/i }));
    await user.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => expect(demoWorkspaceSettings.auto_classify_enabled).toBe(false));
  });

  it('setting a retention value below 1 shows a validation error and blocks saving', async () => {
    const user = userEvent.setup();
    renderSettings();
    await screen.findByText('Data retention');

    await user.type(screen.getByLabelText(/document retention/i), '0');

    expect(await screen.findByText(/at least 1 day/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save changes/i })).toBeDisabled();
  });

  it('an empty retention field is accepted as "keep indefinitely"', async () => {
    const user = userEvent.setup();
    renderSettings();
    await screen.findByText('Data retention');

    await user.type(screen.getByLabelText(/document retention/i), '30');
    await user.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => expect(demoWorkspaceSettings.document_retention_days).toBe(30));
  });
});
