import { create } from 'zustand';

/**
 * The access token is deliberately NOT persisted (no localStorage/
 * sessionStorage — see the project rule against storing long-lived
 * secrets in insecure browser storage). It lives in memory only, lost on
 * page reload, recovered via a silent refresh using the httpOnly
 * refresh-token cookie (see lib/apiClient.ts) — the same flow bootstraps
 * a fresh page load and recovers from an expired access token mid-session.
 *
 * Zustand (not React state/context) because the fetch wrapper needs to
 * read/write the token from outside the React tree.
 */
interface AuthTokenState {
  accessToken: string | null;
  setAccessToken: (token: string | null) => void;
}

export const useAuthTokenStore = create<AuthTokenState>((set) => ({
  accessToken: null,
  setAccessToken: (token) => set({ accessToken: token }),
}));

export function getAccessToken(): string | null {
  return useAuthTokenStore.getState().accessToken;
}

export function setAccessToken(token: string | null): void {
  useAuthTokenStore.getState().setAccessToken(token);
}
