import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import { DEMO_ACCOUNTS, DEMO_ACCOUNT_PASSWORD } from '@/features/auth/demoAccounts';

const API = config.apiBaseUrl;

/** Fixtures matching the real backend contract (apps.accounts /
 * apps.workspaces serializers) — kept here so tests and dev-mode mocking
 * share one source of truth instead of drifting. */
export const demoUser = {
  id: 'user-1',
  email: 'owner@demo.docpilot.ai',
  first_name: 'Demo',
  last_name: 'Owner',
};

export const demoWorkspaces = [
  { id: 'ws-1', name: 'Demo Workspace', slug: 'demo-workspace', role: 'owner' as const },
  { id: 'ws-2', name: 'Second Workspace', slug: 'second-workspace', role: 'viewer' as const },
];

export const DEMO_PASSWORD = 'correct-password';

function errorBody(code: string, message: string) {
  return { error: { code, message, details: null } };
}

/** Default handlers represent a signed-out visitor — the realistic
 * starting state for most tests. Tests needing a signed-in session
 * override these per-test with server.use(...). */
export const handlers = [
  http.get(`${API}/auth/session/`, () =>
    HttpResponse.json(
      errorBody('not_authenticated', 'Authentication credentials were not provided.'),
      { status: 401 },
    ),
  ),

  http.post(`${API}/auth/login/`, async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    if (body.email === demoUser.email && body.password === DEMO_PASSWORD) {
      return HttpResponse.json({ access: 'fake-access-token', user: demoUser });
    }
    // The sign-in page's quick-login buttons (one per DEMO_ACCOUNTS role)
    // authenticate against this same shared demo-password constant.
    const demoAccount = DEMO_ACCOUNTS.find((account) => account.email === body.email);
    if (demoAccount && body.password === DEMO_ACCOUNT_PASSWORD) {
      return HttpResponse.json({
        access: 'fake-access-token',
        user: { id: demoAccount.role, email: demoAccount.email, first_name: 'Demo', last_name: demoAccount.label },
      });
    }
    return HttpResponse.json(errorBody('authentication_failed', 'Invalid email or password.'), {
      status: 401,
    });
  }),

  http.post(`${API}/auth/refresh/`, () =>
    HttpResponse.json(errorBody('authentication_failed', 'No refresh token provided.'), {
      status: 401,
    }),
  ),

  http.post(`${API}/auth/logout/`, () => new HttpResponse(null, { status: 204 })),

  http.patch(`${API}/auth/active-workspace/`, () => new HttpResponse(null, { status: 204 })),
];

/** Handlers for an already-signed-in session (Demo Owner, two
 * workspaces, "Demo Workspace" active) — spread these in via
 * server.use(...signedInHandlers) at the start of a test. */
export const signedInHandlers = [
  http.get(`${API}/auth/session/`, () =>
    HttpResponse.json({
      user: demoUser,
      workspaces: demoWorkspaces,
      active_workspace_id: demoWorkspaces[0]!.id,
    }),
  ),
  http.post(`${API}/auth/refresh/`, () => HttpResponse.json({ access: 'refreshed-access-token' })),
];
