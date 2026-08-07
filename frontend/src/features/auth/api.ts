import { apiRequest } from '@/lib/apiClient';
import type { LoginResponse, SessionResponse } from './types';

export function login(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
    skipAuthRefresh: true,
  });
}

export function logout(): Promise<void> {
  return apiRequest<void>('/auth/logout/', { method: 'POST' });
}

export function getSession(): Promise<SessionResponse> {
  return apiRequest<SessionResponse>('/auth/session/');
}

export function setActiveWorkspace(workspaceId: string): Promise<void> {
  return apiRequest<void>('/auth/active-workspace/', {
    method: 'PATCH',
    body: JSON.stringify({ workspace_id: workspaceId }),
  });
}
