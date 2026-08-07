import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import { server } from '@/mocks/server';
import { signedInHandlers, demoUser, demoWorkspaces } from '@/mocks/handlers';
import { RequireRole } from '@/components/auth/RequireRole';
import { AccessDeniedPage } from '@/pages/AccessDenied';
import { renderWithProviders } from '@/test/testUtils';

const API = config.apiBaseUrl;

function renderGuardedRoute() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/app/settings']}>
      <Routes>
        <Route path="/access-denied" element={<AccessDeniedPage />} />
        <Route path="/app/dashboard" element={<div>Dashboard</div>} />
        <Route element={<RequireRole allowedRoles={['owner', 'admin']} />}>
          <Route path="/app/settings" element={<div>Settings content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('RequireRole', () => {
  it('redirects to /access-denied when the caller lacks an allowed role', async () => {
    server.use(
      http.get(`${API}/auth/session/`, () =>
        HttpResponse.json({
          user: demoUser,
          workspaces: [{ ...demoWorkspaces[0]!, role: 'viewer' }],
          active_workspace_id: demoWorkspaces[0]!.id,
        }),
      ),
      http.post(`${API}/auth/refresh/`, () => HttpResponse.json({ access: 'token' })),
    );

    renderGuardedRoute();

    expect(await screen.findByText("You don't have access to this page")).toBeInTheDocument();
  });

  it('renders the route when the caller has an allowed role', async () => {
    server.use(...signedInHandlers); // demoWorkspaces[0] role is 'owner'

    renderGuardedRoute();

    expect(await screen.findByText('Settings content')).toBeInTheDocument();
  });
});
