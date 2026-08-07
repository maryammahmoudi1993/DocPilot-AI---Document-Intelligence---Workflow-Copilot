import { config } from '@/config';
import { getAccessToken, setAccessToken } from '@/stores/authTokenStore';

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: unknown;
  };
}

/** Thrown for any non-2xx response the backend describes with the stable
 * `{error: {code, message, details}}` envelope — see backend
 * common/exceptions.py. `code` is what callers should branch on, not
 * `message` (which is safe-to-display but not a stable identifier). */
export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error.message);
    this.name = 'ApiError';
    this.code = body.error.code;
    this.status = status;
    this.details = body.error.details;
  }
}

/** Thrown when a request got a 401 and the silent-refresh attempt also
 * failed — the caller (TanStack Query's error state, ProtectedRoute)
 * should treat this as "not signed in" and redirect to sign-in. */
export class SessionExpiredError extends Error {
  constructor() {
    super('Session expired');
    this.name = 'SessionExpiredError';
  }
}

interface RequestOptions extends RequestInit {
  /** Login/refresh themselves must never trigger the refresh-and-retry
   * loop on their own 401s. */
  skipAuthRefresh?: boolean;
}

let refreshPromise: Promise<string> | null = null;

/** Coalesces concurrent refresh attempts into one in-flight request —
 * several queries failing with 401 at once (e.g. on first page load)
 * must not each independently spend the single-use rotating refresh
 * token racing each other. */
function refreshAccessToken(): Promise<string> {
  refreshPromise ??= fetch(`${config.apiBaseUrl}/auth/refresh/`, {
    method: 'POST',
    credentials: 'include',
  })
    .then(async (response) => {
      if (!response.ok) throw new SessionExpiredError();
      const data = (await response.json()) as { access: string };
      setAccessToken(data.access);
      return data.access;
    })
    .finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}

function buildHeaders(init: RequestInit, token: string | null): Headers {
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return headers;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
    if (body?.error) throw new ApiError(response.status, body);
    throw new Error(`Request failed with status ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/**
 * Every request carries `credentials: 'include'` (so the httpOnly
 * refresh cookie is sent) and the in-memory access token if present. A
 * 401 triggers exactly one silent-refresh-and-retry — this is also how
 * session bootstrap on a fresh page load works: no token yet, first
 * request 401s, refresh succeeds from the cookie, retry succeeds.
 */
export async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { skipAuthRefresh, ...init } = options;
  const url = `${config.apiBaseUrl}${endpoint}`;

  const response = await fetch(url, {
    ...init,
    headers: buildHeaders(init, getAccessToken()),
    credentials: 'include',
  });

  if (response.status === 401 && !skipAuthRefresh) {
    let newToken: string;
    try {
      newToken = await refreshAccessToken();
    } catch {
      setAccessToken(null);
      throw new SessionExpiredError();
    }
    const retryResponse = await fetch(url, {
      ...init,
      headers: buildHeaders(init, newToken),
      credentials: 'include',
    });
    return parseResponse<T>(retryResponse);
  }

  return parseResponse<T>(response);
}
