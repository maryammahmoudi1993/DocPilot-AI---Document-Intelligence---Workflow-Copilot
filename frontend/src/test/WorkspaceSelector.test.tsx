import { describe, it, expect } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import { server } from '@/mocks/server';
import { signedInHandlers, demoWorkspaces } from '@/mocks/handlers';
import { WorkspaceSelector } from '@/components/layout/WorkspaceSelector';
import { renderWithProviders } from '@/test/testUtils';

const API = config.apiBaseUrl;

describe('WorkspaceSelector', () => {
  it('shows an error state when the session fails to load', async () => {
    // Default (signed-out) handlers: session 401s and refresh also 401s.
    renderWithProviders(<WorkspaceSelector />);

    expect(await screen.findByText("Couldn't load workspaces")).toBeInTheDocument();
  });

  it('lists every workspace once loaded, with the active one selected', async () => {
    server.use(...signedInHandlers);
    renderWithProviders(<WorkspaceSelector />);

    expect(await screen.findByText(demoWorkspaces[0]!.name)).toBeInTheDocument();
  });

  it('switches the active workspace on selection', async () => {
    server.use(...signedInHandlers);
    let patchedWorkspaceId: string | null = null;
    server.use(
      http.patch(`${API}/auth/active-workspace/`, async ({ request }) => {
        const body = (await request.json()) as { workspace_id: string };
        patchedWorkspaceId = body.workspace_id;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    renderWithProviders(<WorkspaceSelector />);

    await screen.findByText(demoWorkspaces[0]!.name);
    await user.click(screen.getByRole('combobox', { name: 'Active workspace' }));
    await user.click(await screen.findByRole('option', { name: demoWorkspaces[1]!.name }));

    await waitFor(() => expect(patchedWorkspaceId).toBe(demoWorkspaces[1]!.id));
  });

  it('shows a toast and does not crash when switching fails', async () => {
    server.use(...signedInHandlers);
    server.use(
      http.patch(
        `${API}/auth/active-workspace/`,
        () =>
          HttpResponse.json(
            { error: { code: 'permission_denied', message: 'Not a member.', details: null } },
            { status: 403 },
          ),
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<WorkspaceSelector />);

    await screen.findByText(demoWorkspaces[0]!.name);
    await user.click(screen.getByRole('combobox', { name: 'Active workspace' }));
    await user.click(await screen.findByRole('option', { name: demoWorkspaces[1]!.name }));

    expect(await screen.findByText("Couldn't switch workspace")).toBeInTheDocument();
    // The selector itself is still on screen and functional, not crashed.
    expect(screen.getByRole('combobox', { name: 'Active workspace' })).toBeInTheDocument();
  });
});
