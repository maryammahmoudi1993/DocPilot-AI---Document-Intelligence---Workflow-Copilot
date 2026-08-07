import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { renderWithProviders } from '@/test/testUtils';

const API = config.apiBaseUrl;

function renderProtected(initialPath = '/app/dashboard') {
  return renderWithProviders(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/sign-in" element={<div>Sign in page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/app/dashboard" element={<div>Protected dashboard</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProtectedRoute', () => {
  it('redirects to sign-in when there is no valid session (default signed-out handlers)', async () => {
    renderProtected();

    expect(await screen.findByText('Sign in page')).toBeInTheDocument();
  });

  it('renders the protected content once session bootstrap succeeds via silent refresh', async () => {
    // No access token in memory yet (fresh page load) — the first
    // /auth/session/ call 401s, apiClient silently refreshes using the
    // (mocked) cookie, and retries. This is the real bootstrap flow, not
    // a shortcut taken just for the test.
    server.use(...signedInHandlers);
    renderProtected();

    expect(await screen.findByText('Protected dashboard')).toBeInTheDocument();
  });

  it('redirects to sign-in when the session is expired (refresh also fails)', async () => {
    server.use(
      http.get(`${API}/auth/session/`, () =>
        HttpResponse.json(
          { error: { code: 'not_authenticated', message: 'Authentication credentials were not provided.', details: null } },
          { status: 401 },
        ),
      ),
      http.post(`${API}/auth/refresh/`, () =>
        HttpResponse.json(
          { error: { code: 'authentication_failed', message: 'Token is invalid or expired.', details: null } },
          { status: 401 },
        ),
      ),
    );

    renderProtected();

    expect(await screen.findByText('Sign in page')).toBeInTheDocument();
  });
});
