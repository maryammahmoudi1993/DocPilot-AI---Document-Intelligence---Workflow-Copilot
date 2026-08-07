import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from '@tanstack/react-query';
import { setAccessToken } from '@/stores/authTokenStore';
import * as authApi from './api';
import type { SessionResponse } from './types';

export const SESSION_QUERY_KEY = ['auth', 'session'] as const;

export function useSession(options?: Partial<UseQueryOptions<SessionResponse>>) {
  return useQuery({
    queryKey: SESSION_QUERY_KEY,
    queryFn: authApi.getSession,
    // A 401 (not signed in) is expected/routine here, not worth retrying
    // — retrying would also mean re-attempting the refresh-and-retry
    // dance in apiClient multiple times over.
    retry: false,
    ...options,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => authApi.login(email, password),
    onSuccess: (data) => {
      setAccessToken(data.access);
      void queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      // Clear the token and every cached query, not just session — a
      // signed-out user must never see a subsequent signed-in user's
      // stale cached data (or vice versa) on the same device.
      setAccessToken(null);
      queryClient.clear();
    },
  });
}

export function useSetActiveWorkspace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.setActiveWorkspace,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
    },
  });
}
